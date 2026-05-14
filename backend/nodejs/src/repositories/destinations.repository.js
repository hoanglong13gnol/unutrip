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

/**
 * Admin-scoped detail lookup used by `GET /admin/destinations/api/:id`.
 *
 * Phase 4 pilot — distinct from `getDestinationById` because the admin UI
 * does NOT need (and the JSON contract does NOT include) the
 * `is_favorite` join. SQL text and column projection are byte-identical
 * to the previous inline `db.get` call. `db.get` resolves to `undefined`
 * for missing rows, which the admin handler translates into a 404.
 */
export async function getAdminDestinationDetailById(id) {
  return db.get(
    "SELECT id, name, category, description, city, province, address, latitude, longitude, open_time, close_time FROM app_places WHERE id = ?",
    [id]
  );
}

/**
 * Admin-scoped DELETE used by `POST /admin/destinations/delete/:id`.
 *
 * Phase 4 pilot — relies on FK constraints to fan out to dependent
 * tables (`favorites`, `reviews`, `place_images`, `place_id_map`, etc.).
 * SQL is preserved verbatim. The admin UI's confirm prompt warns the
 * operator that the action is not reversible.
 */
export async function deleteDestinationById(id) {
  return db.run("DELETE FROM app_places WHERE id = ?", [id]);
}

/**
 * Admin-scoped listing used by `GET /admin/destinations` (no-search variant).
 *
 * Phase 5 continuation of the Phase 4 pilot — SQL string is byte-identical
 * to the previous inline `db.query` call. The admin HTML template renders
 * `d.id`, `d.name`, `d.city`, `d.province`, `d.category`, `d.rating` by
 * exact column name, so do NOT change the projection.
 */
export async function listAdminDestinations() {
  return db.query(
    "SELECT id, name, city, province, category, rating FROM app_places ORDER BY id DESC"
  );
}

/**
 * Admin-scoped 6-column LIKE search used by `GET /admin/destinations?q=…`.
 *
 * Phase 5 continuation of the Phase 4 pilot — SQL is byte-identical to
 * the previous inline `db.query` call, including the original 11/13/11
 * continuation indentation (preserved so the SQL string content is
 * byte-identical, not merely visually similar). Caller passes the
 * already-`%…%`-wrapped `like` string.
 */
export async function searchAdminDestinations({ like }) {
  return db.query(
    `SELECT id, name, city, province, category, rating FROM app_places
           WHERE name LIKE ? OR city LIKE ? OR IFNULL(province,'') LIKE ? OR IFNULL(address,'') LIKE ?
             OR category LIKE ? OR CAST(id AS CHAR) LIKE ?
           ORDER BY id DESC`,
    [like, like, like, like, like, like]
  );
}

/**
 * Admin-scoped UPDATE used by the `POST /admin/destinations/save` UPDATE
 * branch (when `id` is a positive integer).
 *
 * Phase 5 continuation of the Phase 4 pilot — SQL statement, column
 * order, and `?` placeholder count are byte-identical to the previous
 * inline `db.run` call. Caller pre-coerces `openTime` / `closeTime` to
 * `null` when blank (matches the pre-Phase-5 behavior).
 */
export async function updateAdminDestination({
  id,
  name,
  description,
  address,
  city,
  province,
  latitude,
  longitude,
  category,
  openTime,
  closeTime
}) {
  return db.run(
    `UPDATE app_places
           SET name=?, description=?, address=?, city=?, province=?, latitude=?, longitude=?, category=?, open_time=?, close_time=?
           WHERE id=?`,
    [name, description, address, city, province, latitude, longitude, category, openTime, closeTime, id]
  );
}

/**
 * Admin-scoped next-id lookup used by the `POST /admin/destinations/save`
 * INSERT branch (when `id` is missing or non-positive).
 *
 * Phase 5 continuation of the Phase 4 pilot — returns the raw row exactly
 * as the inline `db.get` did. The admin handler reads `nextRow?.next_id`,
 * so the row shape must keep the `next_id` column name.
 */
export async function getNextAppPlaceId() {
  return db.get("SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM app_places");
}

/**
 * Admin-scoped INSERT used by the `POST /admin/destinations/save` INSERT
 * branch. Phase 5 bakes the default-value literals (`'[]'`, `0`, `0`, `1`,
 * `0`, `0`) into the SQL string as before so the admin handler stops
 * passing them. SQL text and placeholder count are byte-identical.
 */
export async function insertAdminDestination({
  id,
  placeKey,
  name,
  description,
  shortDescription,
  address,
  city,
  province,
  latitude,
  longitude,
  category,
  openTime,
  closeTime
}) {
  return db.run(
    `INSERT INTO app_places (
          id, place_key, name, description, short_description, address, city, province, area,
          latitude, longitude, category, open_time, close_time,
          tags_json, kid_friendly, elderly_friendly, is_active, rating, review_count
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?, ?, ?, '[]', 0, 0, 1, 0, 0)`,
    [
      id,
      placeKey,
      name,
      description,
      shortDescription,
      address,
      city,
      province,
      latitude,
      longitude,
      category,
      openTime,
      closeTime
    ]
  );
}
