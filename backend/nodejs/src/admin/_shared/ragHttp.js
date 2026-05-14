/**
 * Admin-only RAG fetch helpers extracted from `src/admin.js` in Phase 4.
 *
 * Behavior is byte-identical to the originals:
 *  - 3000 ms default timeout for GET (`fetchRagJson`),
 *    5000 ms default for POST (`postRagJson`).
 *  - No retry semantics — admin operators rely on the raw upstream error
 *    shape, so the retry-aware helper in `src/lib/ragUpstream.js` is
 *    intentionally NOT used here.
 *  - On non-JSON bodies, `data = { raw: text }` is returned verbatim.
 *  - On thrown errors, the envelope is
 *    `{ ok:false, status:0, url, data:{ error } }` with `error` produced by
 *    `formatRagFetchError` (which maps `AbortError → "Timeout khi gọi
 *    FastAPI RAG"`).
 */

import {
  ragAdminJsonHeaders,
  ragJsonHeaders,
  ragUrl
} from "../../config/ragClient.js";

export function formatRagFetchError(error) {
  const e = /** @type {Error & { cause?: { code?: string; errno?: string; syscall?: string; address?: string; port?: number } }} */ (
    error
  );
  if (e.name === "AbortError") return "Timeout khi gọi FastAPI RAG";
  const parts = [e.message || String(error)];
  const c = e.cause;
  if (c && typeof c === "object") {
    if (c.code) parts.push(`code=${c.code}`);
    if (c.errno != null) parts.push(`errno=${c.errno}`);
    if (c.syscall) parts.push(`syscall=${c.syscall}`);
    if (c.address != null || c.port != null) {
      parts.push(`target=${c.address ?? "?"}:${c.port ?? "?"}`);
    }
  }
  return parts.join(" | ");
}

export function ragHeadersForPath(pathname) {
  return pathname.startsWith("/admin/") ? ragAdminJsonHeaders() : ragJsonHeaders();
}

export async function fetchRagJson(pathname, timeoutMs = 3000) {
  const url = ragUrl(pathname);
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      signal: controller.signal,
      headers: ragHeadersForPath(pathname)
    });

    const text = await response.text();
    let data;

    try {
      data = text ? JSON.parse(text) : null;
    } catch {
      data = { raw: text };
    }

    return {
      ok: response.ok,
      status: response.status,
      url,
      data
    };
  } catch (error) {
    return {
      ok: false,
      status: 0,
      url,
      data: {
        error: formatRagFetchError(error)
      }
    };
  } finally {
    clearTimeout(timer);
  }
}

export async function postRagJson(pathname, body = {}, timeoutMs = 5000) {
  const url = ragUrl(pathname);
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      method: "POST",
      headers: ragHeadersForPath(pathname),
      body: JSON.stringify(body),
      signal: controller.signal
    });

    const text = await response.text();
    let data;

    try {
      data = text ? JSON.parse(text) : null;
    } catch {
      data = { raw: text };
    }

    return {
      ok: response.ok,
      status: response.status,
      url,
      data
    };
  } catch (error) {
    return {
      ok: false,
      status: 0,
      url,
      data: {
        error: formatRagFetchError(error)
      }
    };
  } finally {
    clearTimeout(timer);
  }
}
