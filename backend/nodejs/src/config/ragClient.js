/**
 * Gọi FastAPI RAG với optional RAG_INTERNAL_API_KEY (header X-RAG-Internal-Key).
 */
import { RAG_BASE_URL } from "./env.js";

function normalizeBase(url) {
  return String(url || "").replace(/\/$/, "");
}

/** Full URL cho path dạng "/rag/chat". */
export function ragUrl(path) {
  const p = path.startsWith("/") ? path : `/${path}`;
  return `${normalizeBase(RAG_BASE_URL)}${p}`;
}

export function ragAuthHeaders(extra = {}) {
  const h = { ...extra };
  const key = process.env.RAG_INTERNAL_API_KEY;
  if (
    key &&
    !h["X-RAG-Internal-Key"] &&
    !String(h.Authorization || "").startsWith("Bearer ")
  ) {
    h["X-RAG-Internal-Key"] = key;
  }
  return h;
}

export function ragJsonHeaders(extra = {}) {
  return ragAuthHeaders({ "Content-Type": "application/json", ...extra });
}
