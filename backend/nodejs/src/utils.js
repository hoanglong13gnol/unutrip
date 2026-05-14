import { randomUUID } from "node:crypto";

export { apiOk, apiFail } from "./shared/http/response.js";

/**
 * @param {import("http").IncomingHttpHeaders} headers
 * @returns {{ requestId: string, traceHeaders: Record<string, string> }}
 */
export function resolveRequestTrace(headers) {
  const raw = headers["x-request-id"];
  const first = Array.isArray(raw) ? raw[0] : raw;
  const trimmed = typeof first === "string" ? first.trim().slice(0, 128) : "";
  const requestId = trimmed.length > 0 ? trimmed : randomUUID();
  return { requestId, traceHeaders: { "X-Request-ID": requestId } };
}

export function parseJsonArray(value, fallback = []) {
  if (!value) return fallback;
  if (Array.isArray(value)) return value;
  try {
    const parsed = typeof value === 'string' ? JSON.parse(value) : value;
    return Array.isArray(parsed) ? parsed : fallback;
  } catch {
    return fallback;
  }
}

export function toIsoDate(dateStr) {
  if (!dateStr) return null;
  // If already yyyy-mm-dd, return as is
  if (/^\d{4}-\d{2}-\d{2}$/.test(dateStr)) return dateStr;
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return null;
    return d.toISOString().slice(0, 10);
  } catch {
    return null;
  }
}

export function daysBetweenInclusive(startISO, endISO) {
  if (!startISO || !endISO) return 1;
  const start = new Date(startISO);
  const end = new Date(endISO);
  if (isNaN(start.getTime()) || isNaN(end.getTime())) return 1;
  
  const ms = end.getTime() - start.getTime();
  const days = Math.floor(ms / 86400000) + 1;
  return Math.max(1, days);
}

