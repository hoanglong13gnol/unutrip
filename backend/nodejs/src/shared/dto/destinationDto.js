/**
 * Destination DTO module — Phase 5 split of `src/routes/helpers.js`.
 *
 * Function bodies are byte-identical copies of the originals. The
 * `getImageUrlValue` and `getDestinationImages` helpers stay private
 * (non-exported) just as they were inside `helpers.js`. `fixUrl` is
 * exported because the user DTO module needs it for the `avatar` field.
 */

import { parseJsonArray } from "../../utils.js";
import * as destinationImagesRepository from "../../repositories/destinationImages.repository.js";

export async function attachDestinationImages(rows) {
  if (!Array.isArray(rows) || rows.length === 0) return rows || [];

  const ids = [...new Set(rows.map((r) => Number(r.id)).filter(Number.isFinite))];
  if (ids.length === 0) return rows;

  const imageRows = await destinationImagesRepository.listActiveByDestinationIds(ids);

  const byDestination = new Map();
  for (const image of imageRows) {
    const destinationId = Number(image.destination_id);
    const url = fixUrl(image.image_url);
    if (!url) continue;
    if (!byDestination.has(destinationId)) byDestination.set(destinationId, []);
    byDestination.get(destinationId).push(url);
  }

  return rows.map((row) => ({
    ...row,
    images_from_table: byDestination.get(Number(row.id)) || []
  }));
}

function getImageUrlValue(value) {
  if (!value) return "";

  if (typeof value === "string") {
    return value;
  }

  if (typeof value === "object") {
    return (
      value.url ||
      value.image_url ||
      value.imageUrl ||
      value.src ||
      value.path ||
      ""
    );
  }

  return String(value);
}

export function fixUrl(value) {
  const url = getImageUrlValue(value).trim();

  if (!url) return "";

  if (url.startsWith("http://") || url.startsWith("https://")) {
    return url;
  }

  if (url.startsWith("/")) {
    return url;
  }

  return `/${url}`;
}

function getDestinationImages(row) {
  if (Array.isArray(row.images_from_table) && row.images_from_table.length > 0) {
    return row.images_from_table.map(fixUrl).filter(Boolean);
  }

  return parseJsonArray(row.images_json, []).map(fixUrl).filter(Boolean);
}

export function normalizeCategoryParam(value) {
  const raw = String(value || "").trim().toLowerCase();
  if (!raw || raw === "all" || raw === "tất cả" || raw === "tat ca") return null;

  const normalized = raw
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/đ/g, "d")
    .replace(/_/g, "-")
    .replace(/\s+/g, " ");

  const map = {
    beach: "beach",
    bien: "beach",
    "bai bien": "beach",

    mountain: "mountain",
    mountains: "mountain",
    nui: "mountain",
    thac: "mountain",
    hang: "mountain",

    city: "city",
    urban: "city",
    "thanh pho": "city",

    heritage: "heritage",
    historical: "heritage",
    history: "heritage",
    "di tich": "heritage",
    "bao tang": "heritage",
    relic: "heritage",
    museum: "heritage",

    nature: "nature",
    natural: "nature",
    "thien nhien": "nature",

    checkin: "checkin",
    "check-in": "checkin",
    "check in": "checkin",
    entertainment: "checkin",
    "giai tri": "checkin",

    food: "food",
    "am thuc": "food",

    culture: "culture",
    "van hoa": "culture",

    religious: "religious",
    spiritual: "religious",
    "tam linh": "religious"
  };

  return map[normalized] || map[raw] || raw || null;
}

export function toDestinationDto(row, isFavorite) {
  return {
    id: row.id,
    name: row.name,
    description: row.description,
    address: row.address,
    city: row.city,
    province: row.province,
    latitude: row.latitude,
    longitude: row.longitude,
    category: row.category,
    images: getDestinationImages(row),
    rating: Number(row.rating ?? 0),
    reviewCount: Number(row.review_count ?? 0),
    openTime: row.open_time ?? null,
    closeTime: row.close_time ?? null,
    entryFee: row.entry_fee ?? null,
    tags: parseJsonArray(row.tags_json, []),
    isFavorite: !!isFavorite
  };
}
