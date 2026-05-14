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

/**
 * FastAPI `/admin/*`: nếu có RAG_ADMIN_API_KEY thì bắt buộc dùng key đó; không thì dùng RAG_INTERNAL_API_KEY
 * (khớp `InternalApiKeyMiddleware._required_api_key` trong RAG).
 */
export function ragAdminAuthHeaders(extra = {}) {
  const h = { ...extra };
  const adminKey = process.env.RAG_ADMIN_API_KEY?.trim();
  const internalKey = process.env.RAG_INTERNAL_API_KEY?.trim();
  const key = adminKey || internalKey;
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

export function ragAdminJsonHeaders(extra = {}) {
  return ragAdminAuthHeaders({ "Content-Type": "application/json", ...extra });
}
