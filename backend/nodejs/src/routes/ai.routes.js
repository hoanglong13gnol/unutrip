import { z } from "zod";
import { db } from "../db.js";
import { authMiddleware } from "../auth.js";
import { parseJsonArray, daysBetweenInclusive, toIsoDate } from "../utils.js";
import { ragJsonHeaders, ragUrl } from "../config/ragClient.js";
import {
  requestItineraryOptions,
  requestItineraryPreview,
  requestLocalAiChatAnswer,
  requestRagChatFallbackForAiChat,
  requestRagChatSimple
} from "../services/ai.service.js";
import * as aiRepository from "../repositories/ai.repository.js";
import {
  flattenSelectedOptionDays,
  resolveDestinationIdsFromSelection
} from "./helpers.js";

export function registerAiRoutes(router) {
  router.post("/ai/suggest-itinerary", authMiddleware, async (req, res) => {
    const schema = z.object({
      preferences: z.array(z.string()).min(1),
      startDate: z.string().min(8),
      endDate: z.string().min(8),
      budget: z.number().optional().nullable(),
      startLocation: z.string().optional().nullable()
    });
    const parsed = schema.safeParse(req.body);
    if (!parsed.success) return res.status(400).json({ success: false, message: "Invalid payload" });

    const { preferences, startDate, endDate, budget } = parsed.data;
    const totalDays = daysBetweenInclusive(startDate, endDate);
    const aiUrl = process.env.AI_MODEL_URL || "http://127.0.0.1:8000/chat";

    try {
      const all = await aiRepository.listDestinationsForAiSuggestion();
      const destinationsInfo = all.map((d) => ({
        id: d.id,
        name: d.name,
        category: d.category,
        rating: d.rating,
        latitude: d.latitude,
        longitude: d.longitude,
        tags: parseJsonArray(d.tags_json, [])
      }));

      const prompt = `Hãy đóng vai hướng dẫn viên du lịch ảo. Tạo lịch trình JSON cho chuyến đi:
Sở thích: ${preferences.join(", ")}
Thời gian: ${totalDays} ngày
Ngân sách: ${budget ? budget + " VNĐ" : "tự do"}

Dữ liệu địa điểm khả dụng (Sử dụng đúng ID):
${JSON.stringify(destinationsInfo.slice(0, 50))}

YÊU CẦU: Trả về JSON đúng cấu trúc:
{
  "title": "Tên chuyến đi",
  "description": "Mô tả",
  "days": [
    { "dayNumber": 1, "items": [{ "destinationId": ID, "startTime": "08:00", "endTime": "10:00", "note": "Ghi chú" }] }
  ]
}`;

      let responseText = "";
      try {
        console.log(`[AI] Generating itinerary for user ${req.user.userId}...`);
        const aiRes = await fetch(aiUrl, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: prompt })
        });
        const aiData = await aiRes.json();
        responseText = aiData.answer;
        console.log(`[AI] Local AI response received (${responseText.length} chars)`);
      } catch (err) {
        console.warn("Local AI failed, falling back to RAG:", err.message);
        const ragRes = await fetch(ragUrl("/rag/chat"), {
          method: "POST",
          headers: ragJsonHeaders(),
          body: JSON.stringify({
            message: `${prompt}\nCHỈ TRẢ VỀ JSON.`,
            top_k: 8,
            mode: "balanced",
            include_prompt: false
          })
        });
        let ragData = {};
        try {
          ragData = await ragRes.json();
        } catch {
          throw new Error("RAG trả về không phải JSON.");
        }
        if (!ragRes.ok) {
          const detail = ragData?.detail ?? ragData?.error;
          throw new Error(
            typeof detail === "string" ? detail : "RAG không khả dụng hoặc từ chối yêu cầu."
          );
        }
        responseText = ragData.answer ?? "";
        if (!responseText) throw new Error("RAG trả về rỗng.");
        console.log(`[AI] RAG fallback response received (${responseText.length} chars)`);
      }

      console.log("[AI] Raw Response Text:", responseText);

      responseText = responseText.replace(/```json\n?|\n?```/g, "").trim();
      let aiResult;
      try {
        aiResult = JSON.parse(responseText);
        console.log("[AI] Parsed JSON days count:", aiResult.days?.length || 0);
      } catch (e) {
        console.error("AI JSON Parse Error:", e, responseText);
        return res.status(500).json({ success: false, message: "AI trả về dữ liệu không hợp lệ." });
      }
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
  });

  router.post("/ai/rag-chat", async (req, res) => {
    try {
      const message = String(req.body?.message || "").trim();
      const topK = Number(req.body?.top_k || 6);
      const mode = String(req.body?.mode || "balanced");

      const targetProvince = req.body?.targetProvince ? String(req.body.targetProvince).trim() : null;

      const targetCity = req.body?.targetCity ? String(req.body.targetCity).trim() : null;

      if (!message) {
        return res.status(400).json({
          success: false,
          message: "Thiếu message"
        });
      }

      const { ragOk, data } = await requestRagChatSimple({
        message,
        top_k: topK,
        mode,
        targetProvince,
        targetCity
      });

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
  });

  router.post("/ai/chat", authMiddleware, async (req, res) => {
    try {
      const message = String(req.body?.message ?? "");
      console.log(`[AI] Chat Request: "${message.substring(0, 50)}..."`);
      const aiUrl = process.env.AI_MODEL_URL || "http://localhost:8000/chat";

      try {
        const { answer } = await requestLocalAiChatAnswer({ aiUrl, message });
        return res.json({ success: true, answer });
      } catch (err) {
        console.warn("Local AI failed, fallback to RAG:", err.message);
        const result = await requestRagChatFallbackForAiChat({ message });

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
      }
    } catch (error) {
      return res.status(500).json({ success: false, message: error.message });
    }
  });

  router.post("/ai/itinerary-preview", authMiddleware, async (req, res) => {
    try {
      const { title, description, startDate, endDate, budget, preferences, province } = req.body;

      const result = await requestItineraryPreview({
        title,
        description,
        startDate,
        endDate,
        budget,
        preferences,
        province
      });

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
  });

  router.post("/ai/itinerary-options", authMiddleware, async (req, res) => {
    try {
      const { title, description, startDate, endDate, budget, preferences, province } = req.body;

      if (!startDate || !endDate) {
        return res.status(400).json({
          success: false,
          message: "Thiếu ngày đi/ngày về",
          data: null
        });
      }

      const result = await requestItineraryOptions({
        title,
        description,
        startDate,
        endDate,
        budget,
        preferences: Array.isArray(preferences) ? preferences : [],
        province
      });

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
  });

  router.post("/itineraries/create-from-option", authMiddleware, async (req, res) => {
    try {
      const { title, description, startDate, endDate, estimatedBudget, budget, optionId, days } = req.body;

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

      const selectedDestinations = flattenSelectedOptionDays(days);

      const resolved = await resolveDestinationIdsFromSelection(selectedDestinations);
      const destinationIds = resolved.destinationIds;
      const unresolved = resolved.unresolved;

      if (destinationIds.length === 0) {
        return res.status(400).json({
          success: false,
          message: "Không map được địa điểm nào sang destinations.id",
          data: {
            optionId: optionId ?? null,
            unresolved
          }
        });
      }

      const start = new Date(startDate);
      const end = new Date(endDate);

      if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) {
        return res.status(400).json({
          success: false,
          message: "Ngày đi/ngày về không hợp lệ",
          data: null
        });
      }

      const totalDays = Math.max(1, Math.floor((end - start) / (1000 * 60 * 60 * 24)) + 1);

      const finalBudget = estimatedBudget ?? budget ?? null;

      const itineraryInfo = await db.run(
        `
      INSERT INTO itineraries
      (user_id, title, description, start_date, end_date, total_days, status, estimated_budget)
      VALUES (?, ?, ?, ?, ?, ?, 'planned', ?)
      `,
        [req.user.userId, title, description ?? null, startDate, endDate, totalDays, finalBudget]
      );

      const itineraryId = Number(itineraryInfo.lastInsertRowid);
      const dayIdByNumber = new Map();

      for (let dayNumber = 1; dayNumber <= totalDays; dayNumber++) {
        const date = new Date(start);
        date.setDate(start.getDate() + dayNumber - 1);

        const dateText = date.toISOString().slice(0, 10);

        const dayInfo = await db.run(
          `
        INSERT INTO itinerary_days (itinerary_id, day_number, date)
        VALUES (?, ?, ?)
        `,
          [itineraryId, dayNumber, dateText]
        );

        dayIdByNumber.set(dayNumber, Number(dayInfo.lastInsertRowid));
      }

      const destinationIdByRawPlaceId = new Map();

      for (const item of selectedDestinations) {
        const directId = item?.destinationId ?? item?.destination_id;
        const rawPlaceId =
          item?.rawPlaceId ?? item?.raw_place_id ?? item?.placeId ?? item?.place_id;

        if (
          directId !== null &&
          directId !== undefined &&
          Number.isInteger(Number(directId)) &&
          Number(directId) > 0
        ) {
          if (rawPlaceId) {
            destinationIdByRawPlaceId.set(String(rawPlaceId), Number(directId));
          }
          continue;
        }

        if (!rawPlaceId) continue;

        const row = await aiRepository.getDestinationIdByRagPlaceId(rawPlaceId);

        if (row?.destination_id) {
          destinationIdByRawPlaceId.set(String(rawPlaceId), Number(row.destination_id));
        }
      }

      const timeSlots = [
        ["08:00", "10:00"],
        ["10:30", "12:00"],
        ["14:00", "16:00"],
        ["16:30", "18:00"]
      ];

      let insertedCount = 0;

      for (const day of days) {
        const dayNumber = Number(day?.dayNumber || 1);
        const dayId = dayIdByNumber.get(dayNumber);

        if (!dayId) continue;

        const items = Array.isArray(day?.items) ? day.items : [];

        for (let index = 0; index < items.length; index++) {
          const item = items[index];
          const rawPlaceId =
            item?.rawPlaceId ?? item?.raw_place_id ?? item?.placeId ?? item?.place_id;

          const directId = item?.destinationId ?? item?.destination_id;

          let destinationId = null;

          if (
            directId !== null &&
            directId !== undefined &&
            Number.isInteger(Number(directId)) &&
            Number(directId) > 0
          ) {
            destinationId = Number(directId);
          } else if (rawPlaceId) {
            destinationId = destinationIdByRawPlaceId.get(String(rawPlaceId));
          }

          if (!destinationId) continue;

          const slot = timeSlots[index % timeSlots.length];

          await db.run(
            `
          INSERT INTO itinerary_items
          (day_id, destination_id, start_time, end_time, note, order_index)
          VALUES (?, ?, ?, ?, ?, ?)
          `,
            [
              dayId,
              destinationId,
              item?.startTime || slot[0],
              item?.endTime || slot[1],
              item?.reason || "Được chọn từ AI tour",
              index + 1
            ]
          );

          insertedCount++;
        }
      }

      return res.json({
        success: true,
        message: "Tạo lịch trình từ tour AI thành công",
        data: {
          id: itineraryId,
          itineraryId,
          optionId: optionId ?? null,
          selectedCount: insertedCount,
          unresolved
        }
      });
    } catch (error) {
      console.error("[CREATE_FROM_OPTION_ERROR]", error);

      return res.status(500).json({
        success: false,
        message: "Lỗi tạo lịch trình từ tour AI: " + error.message,
        data: null
      });
    }
  });

  router.post("/itineraries/create-from-selection", authMiddleware, async (req, res) => {
    try {
      const {
        title,
        description,
        startDate,
        endDate,
        estimatedBudget,
        budget,
        selectedDestinations,
        selectedDestinationIds
      } = req.body;

      if (!title || !startDate || !endDate) {
        return res.status(400).json({
          success: false,
          message: "Thiếu tên lịch trình hoặc ngày đi/ngày về",
          data: null
        });
      }

      let destinationIds = [];
      let unresolved = [];

      if (Array.isArray(selectedDestinationIds) && selectedDestinationIds.length > 0) {
        destinationIds = selectedDestinationIds
          .map((id) => Number(id))
          .filter((id) => Number.isInteger(id) && id > 0);
      } else if (Array.isArray(selectedDestinations) && selectedDestinations.length > 0) {
        const resolved = await resolveDestinationIdsFromSelection(selectedDestinations);
        destinationIds = resolved.destinationIds;
        unresolved = resolved.unresolved;
      }

      if (destinationIds.length === 0) {
        return res.status(400).json({
          success: false,
          message: "Không map được địa điểm nào sang destinations.id",
          data: {
            receivedSelectedDestinations: selectedDestinations ?? null,
            receivedSelectedDestinationIds: selectedDestinationIds ?? null,
            unresolved
          }
        });
      }

      const start = new Date(startDate);
      const end = new Date(endDate);

      if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) {
        return res.status(400).json({
          success: false,
          message: "Ngày đi/ngày về không hợp lệ",
          data: null
        });
      }

      const totalDays = Math.max(1, Math.floor((end - start) / (1000 * 60 * 60 * 24)) + 1);

      const finalBudget = estimatedBudget ?? budget ?? null;

      const itineraryInfo = await db.run(
        `
      INSERT INTO itineraries
      (user_id, title, description, start_date, end_date, total_days, status, estimated_budget)
      VALUES (?, ?, ?, ?, ?, ?, 'planned', ?)
      `,
        [
          req.user.userId,
          title,
          description ?? null,
          startDate,
          endDate,
          totalDays,
          finalBudget
        ]
      );

      const itineraryId = itineraryInfo.lastInsertRowid;
      const dayIds = [];

      for (let dayNumber = 1; dayNumber <= totalDays; dayNumber++) {
        const date = new Date(start);
        date.setDate(start.getDate() + dayNumber - 1);

        const dateText = date.toISOString().slice(0, 10);

        const dayInfo = await db.run(
          `
        INSERT INTO itinerary_days (itinerary_id, day_number, date)
        VALUES (?, ?, ?)
        `,
          [itineraryId, dayNumber, dateText]
        );

        dayIds.push(dayInfo.lastInsertRowid);
      }

      const timeSlots = [
        ["08:00", "10:00"],
        ["10:30", "12:00"],
        ["14:00", "16:00"],
        ["16:30", "18:00"]
      ];

      for (let i = 0; i < destinationIds.length; i++) {
        const dayIndex = i % totalDays;
        const orderIndex = Math.floor(i / totalDays);
        const slot = timeSlots[orderIndex % timeSlots.length];

        await db.run(
          `
        INSERT INTO itinerary_items
        (day_id, destination_id, start_time, end_time, note, order_index)
        VALUES (?, ?, ?, ?, ?, ?)
        `,
          [
            dayIds[dayIndex],
            destinationIds[i],
            slot[0],
            slot[1],
            "Được chọn từ AI gợi ý",
            orderIndex + 1
          ]
        );
      }

      return res.json({
        success: true,
        message: "Tạo lịch trình từ AI gợi ý thành công",
        data: {
          id: itineraryId,
          itineraryId,
          selectedCount: destinationIds.length,
          destinationIds,
          unresolved
        }
      });
    } catch (error) {
      console.error("[CREATE_FROM_SELECTION_ERROR]", error);

      return res.status(500).json({
        success: false,
        message: "Lỗi tạo lịch trình từ lựa chọn: " + error.message,
        data: null
      });
    }
  });
}
