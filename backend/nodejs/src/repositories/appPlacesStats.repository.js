/**
 * Aggregate queries against `app_places` — Phase 5 split out from the
 * inline `db.{query,get}` calls in `admin/aiReport.admin.routes.js`.
 *
 * This file is a brand-new single-purpose repository (separate from
 * `destinations.repository.js`, which owns row-level reads/writes and
 * intentionally does not host aggregate queries). The two SQL strings
 * below are byte-identical copies of the previous inline calls and
 * return the raw `db.{query,get}` row shape — the admin AI-report
 * handler interpolates the rows directly into the LLM prompt and reads
 * `overall?.avgRating`, so the row shape must be preserved exactly.
 */

import { db } from "../db.js";

/**
 * Per-category counts used by `GET /admin/ai-report`'s prompt builder.
 * Returns rows of shape `{ category, count }`.
 */
export async function getCategoryCounts() {
  return db.query("SELECT category, COUNT(*) as count FROM app_places GROUP BY category");
}

/**
 * Overall average rating used by `GET /admin/ai-report`'s prompt builder.
 * Returns a single row of shape `{ avgRating }` (may be `null` when the
 * table is empty — the admin handler converts that to "0.00").
 */
export async function getOverallRatingAverage() {
  return db.get("SELECT AVG(rating) as avgRating FROM app_places");
}
