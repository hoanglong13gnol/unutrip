import { z } from "zod";
import { getResolvedAiModelUrl } from "../../config/env.js";
import { db } from "../../db.js";
import { daysBetweenInclusive, toIsoDate, resolveRequestTrace } from "../../utils.js";
import {
  generateSuggestItineraryAiResult,
  requestItineraryOptions,
  requestItineraryPreview,
  requestLocalAiChatAnswer,
  requestRagChatFallbackForAiChat,
  requestRagChatSimple
} from "../../services/ai.service.js";
import {
  createItineraryFromAiOption,
  createItineraryFromAiSelection
} from "../../services/itineraries.service.js";

export async function suggestItinerary(req, res) {
  const schema = z.object({
    preferences: z.array(z.string()).min(1),
    startDate: z.string().min(8),
    endDate: z.string().min(8),
    budget: z.number().optional().nullable(),
    startLocation: z.string().optional().nullable()
  });
  const parsed = schema.safeParse(req.body);
  if (!parsed.success) return res.status(400).json({ success: false, message: "Invalid payload" });

  const { requestId, traceHeaders } = resolveRequestTrace(req.headers);
  res.setHeader("X-Request-ID", requestId);

  const { preferences, startDate, endDate, budget } = parsed.data;
  const totalDays = daysBetweenInclusive(startDate, endDate);

  try {
    const genResult = await generateSuggestItineraryAiResult({
      preferences,
      startDate,
      endDate,
      budget,
      totalDays,
      userId: req.user.userId,
      traceHeaders
    });

    if (!genResult.ok && genResult.reason === "invalid_ai_json") {
      console.error("AI JSON Parse Error:", genResult.error, genResult.raw);
      return res.status(500).json({ success: false, message: "AI trả về dữ liệu không hợp lệ." });
    }

    const aiResult = genResult.aiResult;

    const isoStart = toIsoDate(startDate);
    const isoEnd = toIsoDate(endDate);

    const conn = await db.pool.getConnection();
    try {
      await conn.beginTransaction();

      const [itinRes] = await conn.execute(
        `
        INSERT INTO itineraries (user_id, title, description, start_date, end_date, total_days, status, estimated_budget)
        VALUES (?, ?, ?, ?, ?, ?, 'planned', ?)
      `,
        [
          req.user.userId,
          aiResult.title || "Lịch trình AI tạo",
          aiResult.description || "Tạo bởi Hướng dẫn viên du lịch ảo.",
          isoStart,
          isoEnd,
          totalDays,
          budget || null
        ]
      );
      const itineraryId = itinRes.insertId;

      if (aiResult.days && Array.isArray(aiResult.days)) {
        for (const day of aiResult.days) {
          const dayDate = new Date(isoStart);
          dayDate.setDate(dayDate.getDate() + ((day.dayNumber || 1) - 1));
          const dayDateStr = toIsoDate(dayDate.toISOString().split("T")[0]);

          const [dayRes] = await conn.execute(
            `
            INSERT INTO itinerary_days (itinerary_id, day_number, date)
            VALUES (?, ?, ?)
          `,
            [itineraryId, day.dayNumber || 1, dayDateStr]
          );
          const dayId = dayRes.insertId;

          let orderIdx = 0;
          if (day.items && Array.isArray(day.items)) {
            for (const item of day.items) {
              await conn.execute(
                `
                INSERT INTO itinerary_items (day_id, destination_id, order_index, start_time, end_time, note)
                VALUES (?, ?, ?, ?, ?, ?)
              `,
                [
                  dayId,
                  item.destinationId,
                  orderIdx++,
                  item.startTime || "08:00",
                  item.endTime || "09:00",
                  item.note || ""
                ]
              );
            }
          }
        }
      }

      await conn.commit();

      const newItin = {
        id: itineraryId,
        userId: req.user.userId,
        title: aiResult.title,
        description: aiResult.description,
        startDate: isoStart,
        endDate: isoEnd,
        totalDays,
        status: "planned",
        estimatedBudget: budget || null
      };
      return res.json({ success: true, itinerary: newItin, message: "Đã tạo lịch trình bằng AI thành công!" });
    } catch (err) {
      await conn.rollback();
      throw err;
    } finally {
      conn.release();
    }
  } catch (error) {
    console.error("AI Itinerary Suggestion Error:", error);
    return res.status(500).json({ success: false, message: "Lỗi tạo lịch trình tự động: " + error.message });
  }
}

export async function ragChat(req, res) {
  const ragChatSchema = z.object({
    message: z.string().trim().min(1).max(8000),
    top_k: z.coerce.number().int().min(1).max(10).optional(),
    mode: z.string().trim().max(64).optional(),
    targetProvince: z.string().trim().max(128).nullable().optional(),
    targetCity: z.string().trim().max(128).nullable().optional()
  });

  const parsed = ragChatSchema.safeParse(req.body);
  if (!parsed.success) {
    return res.status(400).json({
      success: false,
      message: "Payload không hợp lệ",
      errors: parsed.error.flatten()
    });
  }

  const { requestId, traceHeaders } = resolveRequestTrace(req.headers);
  res.setHeader("X-Request-ID", requestId);

  try {
    const { message, top_k: topK = 6, mode = "balanced", targetProvince, targetCity } = parsed.data;

    const { ragOk, data } = await requestRagChatSimple(
      {
        message,
        top_k: topK,
        mode,
        targetProvince: targetProvince ?? null,
        targetCity: targetCity ?? null
      },
      traceHeaders
    );

    if (!ragOk) {
      return res.status(502).json({
        success: false,
        message: "FastAPI RAG trả lỗi",
        data
      });
    }

    return res.json({
      success: true,
      message: "OK",
      answer: data?.answer || "",
      places: data?.places || [],
      warnings: data?.warnings || [],
      latency_ms: data?.latency_ms || null,
      model_used: data?.model_used || null,
      fallback_used: data?.fallback_used ?? null,
      rag_mode: data?.rag_mode || mode,
      runtime_mode: data?.runtime_mode || null,
      raw: data
    });
  } catch (error) {
    return res.status(502).json({
      success: false,
      message: "Không gọi được FastAPI RAG",
      error: error.message
    });
  }
}

export async function chat(req, res) {
  try {
    const message = String(req.body?.message ?? "");
    console.log(`[AI] Chat Request: "${message.substring(0, 50)}..."`);
    const aiUrl = getResolvedAiModelUrl();

    const { requestId, traceHeaders } = resolveRequestTrace(req.headers);
    res.setHeader("X-Request-ID", requestId);

    if (aiUrl) {
      try {
        const { answer } = await requestLocalAiChatAnswer({ aiUrl, message });
        return res.json({ success: true, answer });
      } catch (err) {
        console.warn("Local AI failed, fallback to RAG:", err.message);
      }
    }

    const result = await requestRagChatFallbackForAiChat({ message, traceHeaders });

    if (!result.ok && result.reason === "invalid_json") {
      return res.status(502).json({
        success: false,
        message: "RAG trả về không hợp lệ"
      });
    }
    if (!result.ok && result.reason === "upstream") {
      return res.status(502).json({
        success: false,
        message: result.message
      });
    }
    return res.json({ success: true, answer: result.answer });
  } catch (error) {
    return res.status(500).json({ success: false, message: error.message });
  }
}

export async function itineraryPreview(req, res) {
  try {
    const { requestId, traceHeaders } = resolveRequestTrace(req.headers);
    res.setHeader("X-Request-ID", requestId);

    const { title, description, startDate, endDate, budget, preferences, province } = req.body;

    const result = await requestItineraryPreview(
      {
        title,
        description,
        startDate,
        endDate,
        budget,
        preferences,
        province
      },
      traceHeaders
    );

    if (!result.ok) {
      const { data } = result;
      return res.status(502).json({
        success: false,
        message: data.message || "AI service không trả được gợi ý",
        detail: data
      });
    }

    return res.json(result.data);
  } catch (error) {
    console.error("[AI_PREVIEW_ERROR]", error);
    return res.status(500).json({
      success: false,
      message: "Lỗi preview lịch trình AI: " + error.message
    });
  }
}

export async function itineraryOptions(req, res) {
  try {
    const { requestId, traceHeaders } = resolveRequestTrace(req.headers);
    res.setHeader("X-Request-ID", requestId);

    const { title, description, startDate, endDate, budget, preferences, province } = req.body;

    if (!startDate || !endDate) {
      return res.status(400).json({
        success: false,
        message: "Thiếu ngày đi/ngày về",
        data: null
      });
    }

    const result = await requestItineraryOptions(
      {
        title,
        description,
        startDate,
        endDate,
        budget,
        preferences: Array.isArray(preferences) ? preferences : [],
        province
      },
      traceHeaders
    );

    if (!result.ok) {
      const { data } = result;
      return res.status(502).json({
        success: false,
        message: data?.message || "AI service không trả được phương án tour",
        data: null,
        detail: data
      });
    }

    return res.json(result.data);
  } catch (error) {
    console.error("[AI_ITINERARY_OPTIONS_ERROR]", error);

    return res.status(500).json({
      success: false,
      message: "Lỗi lấy phương án tour AI: " + error.message,
      data: null
    });
  }
}

export async function createFromOption(req, res) {
  try {
    const { title, startDate, endDate, days } = req.body;

    if (!title || !startDate || !endDate) {
      return res.status(400).json({
        success: false,
        message: "Thiếu tên lịch trình hoặc ngày đi/ngày về",
        data: null
      });
    }

    if (!Array.isArray(days) || days.length === 0) {
      return res.status(400).json({
        success: false,
        message: "Tour chưa có danh sách ngày/địa điểm",
        data: null
      });
    }

    const result = await createItineraryFromAiOption({
      userId: req.user.userId,
      payload: req.body
    });

    if (!result.ok && result.reason === "no_mapped_destinations") {
      return res.status(400).json({
        success: false,
        message: "Không map được địa điểm nào sang destinations.id",
        data: {
          optionId: result.optionId ?? null,
          unresolved: result.unresolved
        }
      });
    }

    if (!result.ok && result.reason === "invalid_dates") {
      return res.status(400).json({
        success: false,
        message: "Ngày đi/ngày về không hợp lệ",
        data: null
      });
    }

    return res.json({
      success: true,
      message: "Tạo lịch trình từ tour AI thành công",
      data: result.data
    });
  } catch (error) {
    console.error("[CREATE_FROM_OPTION_ERROR]", error);

    return res.status(500).json({
      success: false,
      message: "Lỗi tạo lịch trình từ tour AI: " + error.message,
      data: null
    });
  }
}

export async function createFromSelection(req, res) {
  try {
    const { title, startDate, endDate } = req.body;

    if (!title || !startDate || !endDate) {
      return res.status(400).json({
        success: false,
        message: "Thiếu tên lịch trình hoặc ngày đi/ngày về",
        data: null
      });
    }

    const result = await createItineraryFromAiSelection({
      userId: req.user.userId,
      payload: req.body
    });

    if (!result.ok && result.reason === "no_mapped_destinations") {
      return res.status(400).json({
        success: false,
        message: "Không map được địa điểm nào sang destinations.id",
        data: {
          receivedSelectedDestinations: result.receivedSelectedDestinations ?? null,
          receivedSelectedDestinationIds: result.receivedSelectedDestinationIds ?? null,
          unresolved: result.unresolved
        }
      });
    }

    if (!result.ok && result.reason === "invalid_dates") {
      return res.status(400).json({
        success: false,
        message: "Ngày đi/ngày về không hợp lệ",
        data: null
      });
    }

    return res.json({
      success: true,
      message: "Tạo lịch trình từ AI gợi ý thành công",
      data: result.data
    });
  } catch (error) {
    console.error("[CREATE_FROM_SELECTION_ERROR]", error);

    return res.status(500).json({
      success: false,
      message: "Lỗi tạo lịch trình từ lựa chọn: " + error.message,
      data: null
    });
  }
}
