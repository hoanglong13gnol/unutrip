import { db } from "../db.js";

export async function getDestinationIdByPlaceId(placeId) {
  const row = await db.get(
    `
    SELECT destination_id FROM rag_places WHERE place_id = ? LIMIT 1
    `,
    [placeId]
  );

  return row?.destination_id ?? null;
}
