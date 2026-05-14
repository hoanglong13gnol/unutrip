/**
 * Admin router factory — Phase 4 module shell.
 *
 * Replaces the monolithic `src/admin.js` (~2000 lines) with a thin
 * registration layer that delegates to per-section route files. Handler
 * bodies and rendered HTML are byte-identical to pre-Phase-4 behavior.
 *
 * Registration order MUST match the order the handlers appeared in the
 * original `admin.js` so any path-overlap precedence is preserved (the
 * current set of paths has no overlap, but the ordering is kept
 * defensively).
 */

import { Router } from "express";
import { registerDashboardAdminRoutes } from "./dashboard.admin.routes.js";
import { registerUsersAdminRoutes } from "./users.admin.routes.js";
import { registerDestinationsAdminRoutes } from "./destinations.admin.routes.js";
import { registerSystemAdminRoutes } from "./system.admin.routes.js";
import { registerRagAiAdminRoutes } from "./ragAi.admin.routes.js";
import { registerAiReportAdminRoutes } from "./aiReport.admin.routes.js";

export function buildAdminRouter() {
  const router = Router();
  registerDashboardAdminRoutes(router);
  registerUsersAdminRoutes(router);
  registerDestinationsAdminRoutes(router);
  registerSystemAdminRoutes(router);
  registerRagAiAdminRoutes(router);
  registerAiReportAdminRoutes(router);
  return router;
}
