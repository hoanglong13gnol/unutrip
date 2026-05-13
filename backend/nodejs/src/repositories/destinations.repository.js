import { db } from "../db.js";

function buildDestinationWhere({ category, province, search }) {
  const where = [];
  const params = [];

  if (category) {
    where.push("category = ?");
    params.push(category);
  }
  if (province) {
    where.push("province = ?");
    params.push(province);
  }
  if (search) {
    where.push("(name LIKE ? OR description LIKE ? OR city LIKE ? OR province LIKE ?)");
    const like = `%${search}%`;
    params.push(like, like, like, like);
  }

  const whereSql = where.length ? `WHERE ${where.join(" AND ")}` : "";
  return { whereSql, params };
}

export async function countDestinations({ category, province, search }) {
  const { whereSql, params } = buildDestinationWhere({ category, province, search });
  const countRow = await db.get(`SELECT COUNT(*) as cnt FROM app_places ${whereSql}`, params);
  return countRow?.cnt ?? 0;
}

export async function listDestinations({ userId, category, province, search, limit, offset }) {
  const { whereSql, params } = buildDestinationWhere({ category, province, search });

  return db.query(
    `
      SELECT d.*,
        EXISTS(SELECT 1 FROM favorites f WHERE f.user_id = ? AND f.destination_id = d.id) as is_favorite
      FROM app_places d
      ${whereSql}
      ORDER BY d.rating DESC, d.review_count DESC, d.id DESC
      LIMIT ? OFFSET ?
    `,
    [userId, ...params, limit, offset]
  );
}

export async function listFeaturedDestinations({ userId, limit = 5 }) {
  return db.query(
    `
      SELECT d.*,
        EXISTS(SELECT 1 FROM favorites f WHERE f.user_id = ? AND f.destination_id = d.id) as is_favorite
      FROM app_places d
      ORDER BY d.rating DESC, d.review_count DESC
      LIMIT ?
    `,
    [userId, limit]
  );
}

export async function listNearbyDestinations({ userId, lat, lng, radiusKm, limit }) {
  return db.query(
    `
      SELECT
        d.*,
        (
          6371 * ACOS(
            LEAST(
              1,
              GREATEST(
                -1,
                COS(RADIANS(?)) *
                COS(RADIANS(d.latitude)) *
                COS(RADIANS(d.longitude) - RADIANS(?)) +
                SIN(RADIANS(?)) *
                SIN(RADIANS(d.latitude))
              )
            )
          )
        ) AS distance_km,
        EXISTS(
          SELECT 1
          FROM favorites f
          WHERE f.user_id = ?
            AND f.destination_id = d.id
        ) AS is_favorite
      FROM app_places d
      WHERE d.latitude IS NOT NULL
        AND d.longitude IS NOT NULL
      HAVING distance_km <= ?
      ORDER BY distance_km ASC, d.rating DESC
      LIMIT ?
      `,
    [lat, lng, lat, userId, radiusKm, limit]
  );
}

export async function getDestinationById({ userId, id }) {
  return db.get(
    `
      SELECT d.*,
        EXISTS(SELECT 1 FROM favorites f WHERE f.user_id = ? AND f.destination_id = d.id) as is_favorite
      FROM app_places d
      WHERE d.id = ?
    `,
    [userId, id]
  );
}
