/**
 * Admin-only HTML helpers extracted from `src/admin.js` in Phase 4.
 * Behavior is byte-identical to the originals — these helpers are only
 * consumed by templates under `src/admin/**`.
 */

export function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

export function renderJsonBox(value) {
  return escapeHtml(JSON.stringify(value ?? {}, null, 2));
}
