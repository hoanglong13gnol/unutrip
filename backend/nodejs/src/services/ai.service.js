import { ragJsonHeaders, ragUrl } from "../config/ragClient.js";

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
