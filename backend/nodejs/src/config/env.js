/**
 * Central place for derived env values and production safety checks.
 * Load root `.env` before reading process.env (ESM imports run before index.js body).
 */
import dotenv from "dotenv";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
dotenv.config({ path: path.resolve(__dirname, "../../../../.env") });

const DEFAULT_JWT_SECRET = "smarttravel_dev_secret_change_me";

/** Base URL FastAPI RAG. Node admin gọi `/admin/*` qua URL này; nếu RAG bật `RAG_ADMIN_API_KEY`, đặt cùng giá trị trong `RAG_ADMIN_API_KEY` (Node) — gửi qua header `X-RAG-Internal-Key`. */
export const RAG_BASE_URL =
  process.env.RAG_BASE_URL ||
  process.env.RAG_API_BASE ||
  "http://127.0.0.1:8001";

export function getJwtSecret() {
  return process.env.JWT_SECRET || DEFAULT_JWT_SECRET;
}

export function isDefaultJwtSecret() {
  return getJwtSecret() === DEFAULT_JWT_SECRET;
}

/**
 * Call once at process startup (before accepting traffic).
 */
export function assertSafeProductionConfig() {
  const nodeEnv = process.env.NODE_ENV || "development";
  if (nodeEnv !== "production") return;

  if (isDefaultJwtSecret()) {
    throw new Error(
      "[config] NODE_ENV=production requires JWT_SECRET to be set (not the dev default)."
    );
  }

  if (!process.env.RAG_INTERNAL_API_KEY?.trim()) {
    console.warn(
      "[config] RAG_INTERNAL_API_KEY is unset. Set the same value in Node and FastAPI RAG for production."
    );
  }
}

function envInt(name, fallback) {
  const raw = process.env[name];
  if (raw === undefined || raw === null || String(raw).trim() === "") return fallback;
  const n = Number.parseInt(String(raw), 10);
  return Number.isFinite(n) ? n : fallback;
}

function envBool(name, fallback = false) {
  const v = process.env[name];
  if (v === undefined || v === null) return fallback;
  return ["1", "true", "yes", "on"].includes(String(v).trim().toLowerCase());
}

/** Max time for a single RAG HTTP request (retrieval + Gemini can be slow). */
export const RAG_FETCH_TIMEOUT_MS = envInt("RAG_FETCH_TIMEOUT_MS", 90_000);

/**
 * Total HTTP attempts per RAG call on transient errors (network, 502/503/504/429).
 * Minimum 1.
 */
export const RAG_FETCH_MAX_ATTEMPTS = Math.max(1, envInt("RAG_FETCH_MAX_ATTEMPTS", 3));

/** Skip RAG probe in GET /api/health/ready (use when RAG is optional in an environment). */
export const HEALTHCHECK_SKIP_RAG = envBool("HEALTHCHECK_SKIP_RAG", false);

/** Timeout for optional local AI_MODEL_URL requests. */
export const AI_MODEL_FETCH_TIMEOUT_MS = envInt("AI_MODEL_FETCH_TIMEOUT_MS", 120_000);

/**
 * URL tùy chọn cho LLM cục bộ: `POST` JSON `{ message }` → `{ answer }` (như `backend/nodejs/server.py`).
 * Khi biến môi trường không set, trả `null` — Node **không** gọi `localhost:8000/chat` nữa; dùng thẳng RAG để tránh chờ timeout và log "fetch failed".
 * Đặt `AI_MODEL_URL` (ví dụ `http://127.0.0.1:8000/chat` hoặc `http://127.0.0.1:8001/chat` nếu chỉ có RAG) khi bạn thật sự có service đó.
 */
export function getResolvedAiModelUrl() {
  const raw = process.env.AI_MODEL_URL;
  if (raw === undefined || raw === null) return null;
  const s = String(raw).trim();
  return s.length ? s : null;
}

/** Node admin → FastAPI `/admin/ai/debug-query` (full RAG + Gemini; cần lâu hơn gọi RAG thường). */
export const RAG_ADMIN_DEBUG_TIMEOUT_MS = envInt("RAG_ADMIN_DEBUG_TIMEOUT_MS", 120_000);
