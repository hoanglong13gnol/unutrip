/**
 * Admin-only shared layout renderer extracted from `src/admin.js` in Phase 4.
 * Phase 6: HTML shell loaded from `src/admin/templates/layout.html` via
 * `adminTemplate.js` — output remains byte-identical when filled with the
 * same `content`, `activePath`, `title`, and optional `cspNonce`.
 */

import { fillAdminTemplate, loadAdminTemplate, scriptNonceAttr } from "./adminTemplate.js";

function navPrefix(activePath, name) {
  return activePath === name ? "sidebar-active" : "";
}

export function renderLayout(content, activePath, title = "Quản trị hệ thống", cspNonce) {
  const base = loadAdminTemplate("layout.html");
  return fillAdminTemplate(base, {
    TITLE: title,
    HEADER_DATE: new Date().toLocaleDateString("vi-VN", {
      weekday: "long",
      year: "numeric",
      month: "long",
      day: "numeric"
    }),
    NAV_DASHBOARD: navPrefix(activePath, "dashboard"),
    NAV_USERS: navPrefix(activePath, "users"),
    NAV_DESTINATIONS: navPrefix(activePath, "destinations"),
    NAV_SYSTEM: navPrefix(activePath, "system"),
    NAV_RAG_AI: navPrefix(activePath, "rag-ai"),
    CONTENT: content,
    TAILWIND_NONCE_ATTR: scriptNonceAttr(cspNonce)
  });
}
