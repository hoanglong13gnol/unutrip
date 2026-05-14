import { db } from "../db.js";

function getRunner(conn) {
  if (!conn) return null;
  return {
    query(sql, params) {
      return conn.execute(sql, params);
    }
  };
}

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

export async function destinationExists(destinationId, conn) {
  const runner = getRunner(conn);
  if (runner) {
    const [rows] = await runner.query("SELECT id FROM app_places WHERE id = ? LIMIT 1", [destinationId]);
    return rows.length > 0;
  }
  const row = await db.get("SELECT id FROM app_places WHERE id = ?", [destinationId]);
  return !!row;
}

export async function insertReview({ userId, destinationId, rating, comment, imagesJson }, conn) {
  const runner = getRunner(conn);
  if (runner) {
    const [result] = await runner.query(
      "INSERT INTO reviews (user_id, destination_id, rating, comment, images_json) VALUES (?, ?, ?, ?, ?)",
      [userId, destinationId, rating, comment, imagesJson]
    );
    return { lastInsertRowid: result.insertId };
  }
  return db.run(
    "INSERT INTO reviews (user_id, destination_id, rating, comment, images_json) VALUES (?, ?, ?, ?, ?)",
    [userId, destinationId, rating, comment, imagesJson]
  );
}

export async function getReviewAggregateByDestinationId(destinationId, conn) {
  const runner = getRunner(conn);
  if (runner) {
    const [rows] = await runner.query(
      "SELECT AVG(rating) as avg, COUNT(*) as cnt FROM reviews WHERE destination_id = ?",
      [destinationId]
    );
    return rows[0];
  }
  return db.get("SELECT AVG(rating) as avg, COUNT(*) as cnt FROM reviews WHERE destination_id = ?", [
    destinationId
  ]);
}

export async function updateDestinationReviewAggregate({ destinationId, rating, reviewCount }, conn) {
  const runner = getRunner(conn);
  if (runner) {
    await runner.query("UPDATE app_places SET rating = ?, review_count = ? WHERE id = ?", [
      rating,
      reviewCount,
      destinationId
    ]);
    return;
  }
  await db.run("UPDATE app_places SET rating = ?, review_count = ? WHERE id = ?", [
    rating,
    reviewCount,
    destinationId
  ]);
}
