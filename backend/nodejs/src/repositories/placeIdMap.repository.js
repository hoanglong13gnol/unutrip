import { db } from "../db.js";

export async function getDestinationIdByRagPlaceId(placeId) {
  const row = await db.get(
    `
      SELECT new_app_place_id AS destination_id
      FROM place_id_map
      WHERE rag_place_id = ?
      LIMIT 1
    `,
    [placeId]
  );

  return row?.destination_id ?? null;
}

export async function getAppPlaceIdByRagPlaceId(placeId) {
  return getDestinationIdByRagPlaceId(placeId);
}
