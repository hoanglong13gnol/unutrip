import { db } from "../db.js";
import { authMiddleware } from "../auth.js";
import {
  attachDestinationImages,
  normalizeCategoryParam,
  toDestinationDto
} from "./helpers.js";

export function registerDestinationRoutes(router) {
  router.get("/destinations", authMiddleware, async (req, res) => {
    const page = Math.max(1, Number(req.query.page ?? 1));
    const limit = Math.min(500, Math.max(1, Number(req.query.limit ?? 20)));
    const offset = (page - 1) * limit;

    const categoryRaw = (req.query.category ?? "").toString().trim() || null;
    const category = normalizeCategoryParam(categoryRaw);
    const province = (req.query.province ?? "").toString().trim() || null;
    const search = (req.query.search ?? "").toString().trim() || null;

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
    const countRow = await db.get(`SELECT COUNT(*) as cnt FROM destinations ${whereSql}`, params);
    const total = countRow.cnt;

    const rows = await db.query(
      `
      SELECT d.*,
        EXISTS(SELECT 1 FROM favorites f WHERE f.user_id = ? AND f.destination_id = d.id) as is_favorite
      FROM destinations d
      ${whereSql}
      ORDER BY d.rating DESC, d.review_count DESC, d.id DESC
      LIMIT ? OFFSET ?
    `,
      [req.user.userId, ...params, limit, offset]
    );

    const rowsWithImages = await attachDestinationImages(rows);
    const data = rowsWithImages.map((r) => toDestinationDto(r, !!r.is_favorite));
    return res.json({ success: true, data, total, page, limit });
  });

  router.get("/destinations/featured", authMiddleware, async (req, res) => {
    const rows = await db.query(
      `
      SELECT d.*,
        EXISTS(SELECT 1 FROM favorites f WHERE f.user_id = ? AND f.destination_id = d.id) as is_favorite
      FROM destinations d
      ORDER BY d.rating DESC, d.review_count DESC
      LIMIT 5
    `,
      [req.user.userId]
    );
    const rowsWithImages = await attachDestinationImages(rows);
    const data = rowsWithImages.map((r) => toDestinationDto(r, !!r.is_favorite));
    return res.json({ success: true, data, total: data.length, page: 1, limit: data.length });
  });

  router.get("/destinations/nearby", authMiddleware, async (req, res) => {
    try {
      const lat = Number(req.query.lat);
      const lng = Number(req.query.lng);
      const radiusKm = Math.max(1, Number(req.query.radiusKm ?? req.query.radius ?? 50));
      const limit = Math.min(100, Math.max(1, Number(req.query.limit ?? 20)));

      if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
        return res.status(400).json({
          success: false,
          message: "Invalid lat/lng",
          data: []
        });
      }

      const rows = await db.query(
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
      FROM destinations d
      WHERE d.latitude IS NOT NULL
        AND d.longitude IS NOT NULL
      HAVING distance_km <= ?
      ORDER BY distance_km ASC, d.rating DESC
      LIMIT ?
      `,
        [lat, lng, lat, req.user.userId, radiusKm, limit]
      );

      console.log("[NEARBY]", {
        lat,
        lng,
        radiusKm,
        limit,
        count: rows.length,
        first: rows.slice(0, 5).map((r) => ({
          id: r.id,
          name: r.name,
          province: r.province,
          latitude: r.latitude,
          longitude: r.longitude,
          distance_km: Number(r.distance_km).toFixed(2)
        }))
      });

      const rowsWithImages = await attachDestinationImages(rows);
      const data = rowsWithImages.map((r) => ({
        ...toDestinationDto(r, !!r.is_favorite),
        distanceKm: Number(r.distance_km ?? 0)
      }));

      return res.json({
        success: true,
        data,
        total: data.length,
        page: 1,
        limit,
        center: { lat, lng },
        radiusKm
      });
    } catch (error) {
      console.error("[NEARBY_ERROR]", error);
      return res.status(500).json({
        success: false,
        message: "Không thể lấy địa điểm gần bạn",
        data: []
      });
    }
  });

  router.get("/destinations/:id", authMiddleware, async (req, res) => {
    const id = Number(req.params.id);
    const row = await db.get(
      `
      SELECT d.*,
        EXISTS(SELECT 1 FROM favorites f WHERE f.user_id = ? AND f.destination_id = d.id) as is_favorite
      FROM destinations d
      WHERE d.id = ?
    `,
      [req.user.userId, id]
    );

    if (!row) return res.status(404).json({ success: false, message: "Not found", data: null });
    const [rowWithImages] = await attachDestinationImages([row]);
    return res.json({
      success: true,
      data: toDestinationDto(rowWithImages, !!row.is_favorite)
    });
  });
}
