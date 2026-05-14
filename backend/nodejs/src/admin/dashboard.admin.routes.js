/**
 * Admin section router: dashboard.
 *
 * Phase 4 split — handler bodies are byte-identical copies of the original
 * `router.get("/dashboard", …)` block in the old `src/admin.js`. The shared
 * `renderLayout` helper now lives in `./_shared/layout.js`.
 */

import { db } from "../db.js";
import { fillAdminTemplate, loadAdminTemplate, scriptNonceAttr } from "./_shared/adminTemplate.js";
import { renderLayout } from "./_shared/layout.js";

export function registerDashboardAdminRoutes(router) {
  // 1. Dashboard
  router.get("/dashboard", async (req, res) => {
    try {
      const stats = await db.get(`
        SELECT
          (SELECT COUNT(*) FROM users) as totalUsers,
          (SELECT COUNT(*) FROM app_places) as totalDestinations,
          (SELECT COUNT(*) FROM itineraries) as totalItineraries
      `);

      const latestUsers = await db.query(`
        SELECT full_name, email, created_at
        FROM users
        ORDER BY created_at DESC
        LIMIT 5
      `);

      const latestUserRows = latestUsers
        .map(
          (u, i) => `
                                <tr class="${i % 2 === 0 ? "bg-white" : "bg-gray-50/40"} hover:bg-blue-50/50 transition duration-150 cursor-pointer">
                                    <td class="px-8 py-5">
                                        <div class="flex items-center">
                                            <div class="w-9 h-9 rounded-full bg-slate-100 flex items-center justify-center text-slate-500 font-bold text-xs mr-3">${u.full_name.charAt(0)}</div>
                                            <span class="font-semibold text-gray-700">${u.full_name}</span>
                                        </div>
                                    </td>
                                    <td class="px-8 py-5 text-gray-600 text-sm font-medium">${u.email}</td>
                                    <td class="px-8 py-5 text-center text-xs font-bold text-gray-400">${new Date(u.created_at).toLocaleDateString("vi-VN")}</td>
                                </tr>
                            `
        )
        .join("");

      const cspNonce = res.locals.cspNonce;
      const content = fillAdminTemplate(loadAdminTemplate("dashboard.content.html"), {
        TOTAL_USERS: stats.totalUsers,
        TOTAL_DESTINATIONS: stats.totalDestinations,
        TOTAL_ITINERARIES: stats.totalItineraries,
        LATEST_USER_ROWS: latestUserRows,
        SCRIPT_NONCE_ATTR: scriptNonceAttr(cspNonce)
      });
      res.send(renderLayout(content, "dashboard", undefined, cspNonce));
    } catch (error) {
      res.status(500).send("Admin Dashboard Error: " + error.message);
    }
  });
}
