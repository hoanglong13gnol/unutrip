import { db } from "../db.js";

export async function listDestinationsForAiSuggestion() {
  return db.query("SELECT id, name, category, rating, latitude, longitude, tags_json FROM destinations");
}

export async function getDestinationIdByRagPlaceId(placeId) {
  return db.get(
    `
    SELECT destination_id FROM rag_places WHERE place_id = ? LIMIT 1
    `,
    [placeId]
  );
}
