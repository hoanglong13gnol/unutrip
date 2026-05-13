import { db } from "../db.js";
import { parseJsonArray } from "../utils.js";

export function flattenSelectedOptionDays(days) {
  const selectedDestinations = [];

  for (const day of days || []) {
    const dayNumber = Number(day?.dayNumber || 1);
    const items = Array.isArray(day?.items) ? day.items : [];

    for (const item of items) {
      selectedDestinations.push({
        ...item,
        recommendedDay: dayNumber
      });
    }
  }

  return selectedDestinations;
}

export async function resolveDestinationIdsFromSelection(selectedDestinations) {
  const resolvedIds = [];
  const unresolved = [];

  for (const item of selectedDestinations || []) {
    const directId = item?.destinationId ?? item?.destination_id;

    if (
      directId !== null &&
      directId !== undefined &&
      Number.isInteger(Number(directId)) &&
      Number(directId) > 0
    ) {
      resolvedIds.push(Number(directId));
      continue;
    }

    const rawPlaceId =
      item?.rawPlaceId ??
      item?.raw_place_id ??
      item?.placeId ??
      item?.place_id;

    if (!rawPlaceId) {
      unresolved.push({
        item,
        reason: "missing rawPlaceId/destinationId"
      });
      continue;
    }

    const row = await db.get(
      `
      SELECT destination_id
      FROM rag_places
      WHERE place_id = ?
      LIMIT 1
      `,
      [rawPlaceId]
    );

    if (!row || !row.destination_id) {
      unresolved.push({
        rawPlaceId,
        reason: "not found in rag_places or destination_id is null"
      });
      continue;
    }

    resolvedIds.push(Number(row.destination_id));
  }

  return {
    destinationIds: [...new Set(resolvedIds)],
    unresolved
  };
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

export function toUserDto(row) {
  return {
    id: row.id,
    fullName: row.full_name,
    email: row.email,
    phone: row.phone ?? null,
    avatar: fixUrl(row.avatar),
    preferences: parseJsonArray(row.preferences_json, []),
    createdAt: row.created_at ?? null
  };
}

export async function attachDestinationImages(rows) {
  if (!Array.isArray(rows) || rows.length === 0) return rows || [];

  const ids = [...new Set(rows.map((r) => Number(r.id)).filter(Number.isFinite))];
  if (ids.length === 0) return rows;

  const placeholders = ids.map(() => "?").join(",");
  const imageRows = await db.query(
    `SELECT destination_id, image_url
     FROM destination_images
     WHERE status = 'active'
       AND destination_id IN (${placeholders})
     ORDER BY is_primary DESC, id ASC`,
    ids
  );

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

export function itineraryRowToDto(row, days) {
  return {
    id: row.id,
    userId: row.user_id,
    title: row.title,
    description: row.description ?? null,
    startDate: row.start_date,
    endDate: row.end_date,
    totalDays: row.total_days,
    status: row.status,
    days: days ?? null,
    estimatedBudget: row.estimated_budget ?? null,
    createdAt: row.created_at
  };
}

export async function getUserById(id) {
  const user = await db.get(
    "SELECT id, full_name, email, phone, avatar, preferences_json, created_at FROM users WHERE id = ?",
    [id]
  );
  if (!user) throw new Error("User not found");
  return user;
}

export function firstArrayValue(obj) {
  if (!obj || typeof obj !== "object") return null;
  for (const v of Object.values(obj)) {
    if (Array.isArray(v)) return v;
  }
  return null;
}
