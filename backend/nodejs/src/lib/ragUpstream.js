/**
 * HTTP client for FastAPI RAG: timeout + limited retries on transient failures.
 */
import { ragJsonHeaders, ragUrl } from "../config/ragClient.js";
import { RAG_FETCH_MAX_ATTEMPTS, RAG_FETCH_TIMEOUT_MS } from "../config/env.js";

/**
 * @param {number} status
 */
function isTransientHttpStatus(status) {
  return status === 429 || status === 502 || status === 503 || status === 504;
}

/**
 * @param {unknown} err
 */
function isTransientNetworkError(err) {
  if (!err || typeof err !== "object") return false;
  const name = /** @type {{ name?: string }} */ (err).name;
  if (name === "AbortError") return false;
  const code = /** @type {{ cause?: { code?: string } }} */ (err).cause?.code;
  if (code === "ECONNRESET" || code === "ETIMEDOUT" || code === "ECONNREFUSED") {
    return true;
  }
  const msg = String(/** @type {Error} */ (err).message || "").toLowerCase();
  return (
    msg.includes("fetch failed") ||
    msg.includes("network") ||
    msg.includes("socket") ||
    msg.includes("econnrefused")
  );
}

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

/**
 * POST JSON to RAG. Parses body as JSON when possible.
 *
 * @param {string} path e.g. "/rag/chat/simple"
 * @param {object} body JSON-serializable
 * @param {Record<string, string>} [traceHeaders]
 * @returns {Promise<{ ok: boolean, status: number, data: object | null, rawText: string, error?: string }>}
 */
export async function ragPostJson(path, body, traceHeaders = {}) {
  const url = ragUrl(path);
  const headers = ragJsonHeaders(traceHeaders);
  const maxAttempts = RAG_FETCH_MAX_ATTEMPTS;

  let lastError = /** @type {string | undefined} */ (undefined);
  let lastStatus = 0;
  let lastRawText = "";
  let lastData = /** @type {object | null} */ (null);

  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    const timer = AbortSignal.timeout(RAG_FETCH_TIMEOUT_MS);
    try {
      const res = await fetch(url, {
        method: "POST",
        headers,
        body: JSON.stringify(body),
        signal: timer
      });

      lastStatus = res.status;
      lastRawText = await res.text();

      try {
        lastData = lastRawText ? JSON.parse(lastRawText) : null;
      } catch {
        lastData = { _parseError: true, raw: lastRawText };
      }

      if (res.ok) {
        return { ok: true, status: res.status, data: lastData, rawText: lastRawText };
      }

      const transient = isTransientHttpStatus(res.status);
      lastError = `HTTP ${res.status}`;
      if (transient && attempt < maxAttempts) {
        await sleep(200 * attempt);
        continue;
      }

      return {
        ok: false,
        status: res.status,
        data: lastData,
        rawText: lastRawText,
        error: lastError
      };
    } catch (err) {
      const e = /** @type {Error} */ (err);
      lastError = e.name === "AbortError" ? `timeout after ${RAG_FETCH_TIMEOUT_MS}ms` : e.message;
      const transient = e.name === "AbortError" || isTransientNetworkError(err);
      if (transient && attempt < maxAttempts) {
        await sleep(200 * attempt);
        continue;
      }
      return {
        ok: false,
        status: lastStatus || 0,
        data: lastData,
        rawText: lastRawText,
        error: lastError
      };
    }
  }

  return {
    ok: false,
    status: lastStatus || 0,
    data: lastData,
    rawText: lastRawText,
    error: lastError || "unknown"
  };
}
