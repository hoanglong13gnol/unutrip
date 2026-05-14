/**
 * Admin section router: system.
 *
 * Phase 4 split — handler body is a byte-identical copy of the original
 * `router.get("/system", …)` block in the old `src/admin.js`.
 */

import { db } from "../db.js";
import { fillAdminTemplate, loadAdminTemplate } from "./_shared/adminTemplate.js";
import { renderLayout } from "./_shared/layout.js";

export function registerSystemAdminRoutes(router) {
  // 4. Hệ thống
  router.get("/system", async (req, res) => {
    const stats = await db.get("SELECT COUNT(*) as c FROM itineraries");
    const cspNonce = res.locals.cspNonce;
    const content = fillAdminTemplate(loadAdminTemplate("system.content.html"), {
      ITINERARY_COUNT: stats.c
    });
    res.send(renderLayout(content, "system", "Hệ thống", cspNonce));
  });
}
