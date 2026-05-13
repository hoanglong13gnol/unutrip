import { ragJsonHeaders, ragUrl } from "../config/ragClient.js";
import { parseJsonArray } from "../utils.js";
import * as aiRepository from "../repositories/ai.repository.js";

/**
 * Proxies itinerary preview to RAG. Does not send HTTP responses.
 * @param {object} payload — JSON body (title, description, startDate, endDate, budget, preferences, province)
 * @returns {Promise<{ ok: true, data: object } | { ok: false, status: 502, data: object }>}
 */
export async function requestItineraryPreview(payload) {
  const ragResult = await fetch(ragUrl("/ai/itinerary-preview"), {
    method: "POST",
    headers: ragJsonHeaders(),
    body: JSON.stringify(payload)
  });

  const data = await ragResult.json();

  if (!ragResult.ok || data.success === false) {
    return { ok: false, status: 502, data };
  }

  return { ok: true, data };
}

/**
 * Proxies itinerary options to RAG. Does not send HTTP responses.
 * @param {object} payload — JSON body (preferences should already be an array when required)
 * @returns {Promise<{ ok: true, data: object | null } | { ok: false, status: 502, data: object | null }>}
 */
export async function requestItineraryOptions(payload) {
  const ragResult = await fetch(ragUrl("/ai/itinerary-options"), {
    method: "POST",
    headers: ragJsonHeaders(),
    body: JSON.stringify(payload)
  });

  const text = await ragResult.text();

  let data;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = { raw: text };
  }

  if (!ragResult.ok || data?.success === false) {
    return { ok: false, status: 502, data };
  }

  return { ok: true, data };
}

/**
 * Proxies simple RAG chat. Caller supplies coerced body fields. Does not send HTTP responses.
 * Network errors propagate to the route catch.
 * @param {{ message: string, top_k: number, mode: string, targetProvince: string | null, targetCity: string | null }} payload
 * @returns {Promise<{ ragOk: boolean, data: object | null }>}
 */
export async function requestRagChatSimple(payload) {
  const ragResponse = await fetch(ragUrl("/rag/chat/simple"), {
    method: "POST",
    headers: ragJsonHeaders(),
    body: JSON.stringify(payload)
  });

  const text = await ragResponse.text();

  let data;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = { raw: text };
  }

  return { ragOk: ragResponse.ok, data };
}

/**
 * Local AI chat for /ai/chat. Does not check HTTP ok. Throws on fetch/json failure.
 * @param {{ aiUrl: string, message: string }} params
 * @returns {Promise<{ answer: unknown }>}
 */
export async function requestLocalAiChatAnswer({ aiUrl, message }) {
  const aiRes = await fetch(aiUrl, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message })
  });
  const data = await aiRes.json();
  return { answer: data.answer };
}

/**
 * RAG fallback for /ai/chat only: json() parse (not text+parse). Fetch errors propagate.
 * @param {{ message: string }} params
 * @returns {Promise<
 *   | { ok: true, answer: string }
 *   | { ok: false, reason: "invalid_json" }
 *   | { ok: false, reason: "upstream", message: string }
 * >}
 */
export async function requestRagChatFallbackForAiChat({ message }) {
  const ragRes = await fetch(ragUrl("/rag/chat/simple"), {
    method: "POST",
    headers: ragJsonHeaders(),
    body: JSON.stringify({
      message,
      top_k: 6,
      mode: "balanced"
    })
  });

  let ragData = {};
  try {
    ragData = await ragRes.json();
  } catch {
    return { ok: false, reason: "invalid_json" };
  }

  if (!ragRes.ok) {
    return {
      ok: false,
      reason: "upstream",
      message:
        typeof ragData?.detail === "string"
          ? ragData.detail
          : "AI / RAG không khả dụng"
    };
  }

  return { ok: true, answer: ragData.answer ?? "" };
}

/**
 * /ai/suggest-itinerary model pipeline: catalog → prompt → local AI → RAG fallback → strip → parse.
 * Throws on local/RAG failures (route outer catch). Returns invalid_ai_json on JSON.parse failure.
 *
 * @param {{ preferences: string[], startDate: string, endDate: string, budget: number | null | undefined, totalDays: number, userId: number }} params
 * @returns {Promise<{ ok: true, aiResult: object } | { ok: false, reason: "invalid_ai_json", raw: string, error: unknown }>}
 */
export async function generateSuggestItineraryAiResult({
  preferences,
  startDate: _startDate,
  endDate: _endDate,
  budget,
  totalDays,
  userId
}) {
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

  const aiUrl = process.env.AI_MODEL_URL || "http://127.0.0.1:8000/chat";

  let responseText = "";
  try {
    console.log(`[AI] Generating itinerary for user ${userId}...`);
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
    return { ok: false, reason: "invalid_ai_json", raw: responseText, error: e };
  }

  return { ok: true, aiResult };
}
