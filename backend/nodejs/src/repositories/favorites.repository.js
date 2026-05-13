import { db } from "../db.js";

export async function listFavoriteDestinationsByUserId(userId) {
  return db.query(
    `
      SELECT d.*, 1 as is_favorite
      FROM favorites f
      JOIN app_places d ON d.id = f.destination_id
      WHERE f.user_id = ?
      ORDER BY f.created_at DESC
    `,
    [userId]
  );
}

export async function destinationExists(destinationId) {
  const row = await db.get("SELECT id FROM app_places WHERE id = ?", [destinationId]);
  return !!row;
}

export async function insertFavoriteIgnore(userId, destinationId) {
  await db.run("INSERT IGNORE INTO favorites (user_id, destination_id) VALUES (?, ?)", [
    userId,
    destinationId
  ]);
}

export async function deleteFavorite(userId, destinationId) {
  await db.run("DELETE FROM favorites WHERE user_id = ? AND destination_id = ?", [
    userId,
    destinationId
  ]);
}
