import { normalizeCategoryParam } from "../../shared/dto/destinationDto.js";
import * as destinationsService from "../../services/destinations.service.js";

export async function listDestinations(req, res) {
  const page = Math.max(1, Number(req.query.page ?? 1));
  const limit = Math.min(500, Math.max(1, Number(req.query.limit ?? 20)));
  const offset = (page - 1) * limit;

  const categoryRaw = (req.query.category ?? "").toString().trim() || null;
  const category = normalizeCategoryParam(categoryRaw);
  const province = (req.query.province ?? "").toString().trim() || null;
  const search = (req.query.search ?? "").toString().trim() || null;

  const { total, data } = await destinationsService.listDestinationsPage({
    userId: req.user.userId,
    category,
    province,
    search,
    limit,
    offset
  });
  return res.json({ success: true, data, total, page, limit });
}

export async function listFeatured(req, res) {
  const data = await destinationsService.listFeaturedDestinationsForUser({
    userId: req.user.userId,
    limit: 5
  });
  return res.json({ success: true, data, total: data.length, page: 1, limit: data.length });
}

export async function listNearby(req, res) {
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

    const data = await destinationsService.listNearbyDestinationsForUser({
      userId: req.user.userId,
      lat,
      lng,
      radiusKm,
      limit
    });

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
}

export async function getDestinationDetail(req, res) {
  const id = Number(req.params.id);
  const result = await destinationsService.getDestinationDetail({ userId: req.user.userId, id });

  if (!result.ok) return res.status(404).json({ success: false, message: "Not found", data: null });
  return res.json({
    success: true,
    data: result.data
  });
}
