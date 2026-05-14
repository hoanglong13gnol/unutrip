import { db } from "../db.js";

/**
 * Catalog rows for `/ai/suggest-itinerary` prompt building (v2: `app_places`).
 * IDs match legacy `destinations.id` in the first v2 cut; `ORDER BY id ASC` stabilizes `.slice(0, 50)`.
 */
export async function listDestinationsForAiSuggestion() {
  return db.query(
    "SELECT id, name, category, rating, latitude, longitude, tags_json FROM app_places ORDER BY id ASC"
  );
}
