/**
 * Admin-only category helpers extracted from `src/admin.js` in Phase 4.
 * Behavior is byte-identical to the originals.
 */

/** Giá trị hợp lệ cho cột enum `app_places.category` (migration v2). */
export const APP_PLACE_CATEGORY_ENUM = new Set([
  "beach",
  "checkin",
  "city",
  "culture",
  "food",
  "heritage",
  "mountain",
  "nature",
  "religious",
  "other"
]);

export function normalizeAppPlaceCategory(category) {
  const c = String(category || "")
    .trim()
    .toLowerCase();
  if (!c) return "other";
  if (c === "historical") return "heritage";
  if (c === "entertainment") return "other";
  if (APP_PLACE_CATEGORY_ENUM.has(c)) return c;
  return "other";
}
