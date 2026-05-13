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
