import { db } from "../db.js";

export async function listReviewsByDestinationId(destinationId) {
  return db.query(
    `
      SELECT r.id, r.user_id, u.full_name as user_name, u.avatar as user_avatar,
             r.destination_id, r.rating, r.comment, r.images_json, r.created_at
      FROM reviews r
      JOIN users u ON u.id = r.user_id
      WHERE r.destination_id = ?
      ORDER BY r.created_at DESC, r.id DESC
    `,
    [destinationId]
  );
}

export async function destinationExists(destinationId) {
  const row = await db.get("SELECT id FROM destinations WHERE id = ?", [destinationId]);
  return !!row;
}

export async function insertReview({ userId, destinationId, rating, comment, imagesJson }) {
  return db.run(
    "INSERT INTO reviews (user_id, destination_id, rating, comment, images_json) VALUES (?, ?, ?, ?, ?)",
    [userId, destinationId, rating, comment, imagesJson]
  );
}

export async function getReviewAggregateByDestinationId(destinationId) {
  return db.get("SELECT AVG(rating) as avg, COUNT(*) as cnt FROM reviews WHERE destination_id = ?", [
    destinationId
  ]);
}

export async function updateDestinationReviewAggregate({ destinationId, rating, reviewCount }) {
  await db.run("UPDATE destinations SET rating = ?, review_count = ? WHERE id = ?", [
    rating,
    reviewCount,
    destinationId
  ]);
}
