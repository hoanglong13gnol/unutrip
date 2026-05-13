import { authMiddleware } from "../auth.js";
import * as destinationsRepository from "../repositories/destinations.repository.js";
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

    const total = await destinationsRepository.countDestinations({ category, province, search });
    const rows = await destinationsRepository.listDestinations({
      userId: req.user.userId,
      category,
      province,
      search,
      limit,
      offset
    });

    const rowsWithImages = await attachDestinationImages(rows);
    const data = rowsWithImages.map((r) => toDestinationDto(r, !!r.is_favorite));
    return res.json({ success: true, data, total, page, limit });
  });

  router.get("/destinations/featured", authMiddleware, async (req, res) => {
    const rows = await destinationsRepository.listFeaturedDestinations({ userId: req.user.userId, limit: 5 });
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

      const rows = await destinationsRepository.listNearbyDestinations({
        userId: req.user.userId,
        lat,
        lng,
        radiusKm,
        limit
      });

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
    const row = await destinationsRepository.getDestinationById({ userId: req.user.userId, id });

    if (!row) return res.status(404).json({ success: false, message: "Not found", data: null });
    const [rowWithImages] = await attachDestinationImages([row]);
    return res.json({
      success: true,
      data: toDestinationDto(rowWithImages, !!row.is_favorite)
    });
  });
}
