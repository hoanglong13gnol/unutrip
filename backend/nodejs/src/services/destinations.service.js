import * as destinationsRepository from "../repositories/destinations.repository.js";
import { attachDestinationImages, toDestinationDto } from "../shared/dto/destinationDto.js";

export async function listDestinationsPage({ userId, category, province, search, limit, offset }) {
  const total = await destinationsRepository.countDestinations({ category, province, search });
  const rows = await destinationsRepository.listDestinations({
    userId,
    category,
    province,
    search,
    limit,
    offset
  });
  const rowsWithImages = await attachDestinationImages(rows);
  const data = rowsWithImages.map((r) => toDestinationDto(r, !!r.is_favorite));
  return { total, data };
}

export async function listFeaturedDestinationsForUser({ userId, limit }) {
  const rows = await destinationsRepository.listFeaturedDestinations({ userId, limit });
  const rowsWithImages = await attachDestinationImages(rows);
  return rowsWithImages.map((r) => toDestinationDto(r, !!r.is_favorite));
}

export async function listNearbyDestinationsForUser({ userId, lat, lng, radiusKm, limit }) {
  const rows = await destinationsRepository.listNearbyDestinations({
    userId,
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
  return rowsWithImages.map((r) => {
    const raw = r.distance_km;
    const n = raw == null || raw === "" ? NaN : Number(raw);
    const distanceKm = Number.isFinite(n) && n >= 0 ? n : null;
    return {
      ...toDestinationDto(r, !!r.is_favorite),
      distanceKm
    };
  });
}

export async function getDestinationDetail({ userId, id }) {
  const row = await destinationsRepository.getDestinationById({ userId, id });
  if (!row) {
    return { ok: false };
  }
  const [rowWithImages] = await attachDestinationImages([row]);
  return {
    ok: true,
    data: toDestinationDto(rowWithImages, !!row.is_favorite)
  };
}
