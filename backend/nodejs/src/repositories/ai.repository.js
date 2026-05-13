import { db } from "../db.js";

export async function listDestinationsForAiSuggestion() {
  return db.query("SELECT id, name, category, rating, latitude, longitude, tags_json FROM destinations");
}
