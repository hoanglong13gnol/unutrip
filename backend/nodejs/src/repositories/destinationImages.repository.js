import { db } from "../db.js";

export async function listActiveByDestinationIds(destinationIds) {
  if (!Array.isArray(destinationIds) || destinationIds.length === 0) return [];

  const placeholders = destinationIds.map(() => "?").join(",");

  const rows = await db.query(
    `SELECT app_place_id AS destination_id, image_url
     FROM place_images
     WHERE status = 'active'
       AND app_place_id IN (${placeholders})
     ORDER BY is_primary DESC, id ASC`,
    destinationIds
  );

  return rows;
}
