import { db } from "../db.js";
import { daysBetweenInclusive, toIsoDate } from "../utils.js";
import * as itinerariesRepository from "../repositories/itineraries.repository.js";
import * as aiRepository from "../repositories/ai.repository.js";
import {
  flattenSelectedOptionDays,
  itineraryRowToDto,
  resolveDestinationIdsFromSelection,
  toDestinationDto
} from "../routes/helpers.js";

export async function listItinerariesForUser(userId) {
  const rows = await itinerariesRepository.listItinerariesByUserId(userId);
  return rows.map((r) => itineraryRowToDto(r, null));
}

export async function getItineraryForUser({ userId, itineraryId }) {
  return itinerariesRepository.getItineraryByIdForUser({ itineraryId, userId });
}

export async function getItineraryDetailForUser({ userId, itineraryId }) {
  const it = await itinerariesRepository.getItineraryByIdForUser({ itineraryId, userId });
  if (!it) {
    return { ok: false };
  }

  const days = await itinerariesRepository.listItineraryDaysByItineraryId(itineraryId);
  const dayDtos = [];
  for (const d of days) {
    const items = await itinerariesRepository.listItineraryItemsWithDestinationByDayId(d.id);
    dayDtos.push({
      id: d.id,
      itineraryId: d.itinerary_id,
      dayNumber: d.day_number,
      date: d.date,
      items: items.map((i) => ({
        id: i.id,
        dayId: i.day_id,
        destinationId: i.destination_id,
        destination: toDestinationDto(i, false),
        startTime: i.start_time,
        endTime: i.end_time,
        note: i.note,
        orderIndex: i.order_index
      }))
    });
  }

  return { ok: true, data: itineraryRowToDto(it, dayDtos) };
}

export async function createItineraryWithDaysAndItems({ userId, payload }) {
  const {
    title,
    description,
    startDate,
    endDate,
    destinationIds,
    estimatedBudget,
    totalDays
  } = payload;

  const info = await itinerariesRepository.insertItinerary({
    userId,
    title,
    description,
    startDate: toIsoDate(startDate),
    endDate: toIsoDate(endDate),
    totalDays,
    estimatedBudget
  });

  const itineraryId = Number(info.lastInsertRowid);
  const destIds = Array.isArray(destinationIds) ? destinationIds : [];

  for (let d = 0; d < totalDays; d++) {
    const date = new Date(toIsoDate(startDate));
    date.setDate(date.getDate() + d);
    const dayInfo = await itinerariesRepository.insertItineraryDay({
      itineraryId,
      dayNumber: d + 1,
      date: toIsoDate(date)
    });
    const dayId = Number(dayInfo.lastInsertRowid);

    const chunk = destIds.slice(d * 2, d * 2 + 2);
    for (const [idx, destId] of chunk.entries()) {
      await itinerariesRepository.insertItineraryItem({
        dayId,
        destinationId: destId,
        startTime: idx === 0 ? "09:00" : "14:00",
        endTime: idx === 0 ? "12:00" : "17:00",
        note: null,
        orderIndex: idx
      });
    }
  }

  const it = await itinerariesRepository.getItineraryById(itineraryId);
  return itineraryRowToDto(it, null);
}

export async function addItineraryItem({ userId, itineraryId, payload }) {
  const { destinationId, dayId, startTime, endTime, note } = payload;

  if (!destinationId) {
    return { ok: false, reason: "missing_destination_id" };
  }

  const it = await itinerariesRepository.getItineraryByIdForUser({
    itineraryId,
    userId
  });
  if (!it) {
    return { ok: false, reason: "not_authorized" };
  }

  let targetDayId = dayId;
  if (!targetDayId) {
    const firstDayId = await itinerariesRepository.getFirstItineraryDayId(itineraryId);
    if (!firstDayId) {
      return { ok: false, reason: "no_days" };
    }
    targetDayId = firstDayId;
  }

  const maxIdx = await itinerariesRepository.getMaxOrderIndexByDayId(targetDayId);
  const nextIdx = (maxIdx ?? -1) + 1;

  await itinerariesRepository.insertItineraryItem({
    dayId: targetDayId,
    destinationId,
    orderIndex: nextIdx,
    startTime: startTime || "09:00",
    endTime: endTime || "10:00",
    note: note || ""
  });

  return { ok: true };
}

export async function updateItineraryForUser({ userId, itineraryId, payload }) {
  const {
    title,
    description,
    startDate,
    endDate,
    totalDays,
    status,
    estimatedBudget
  } = payload;

  await itinerariesRepository.updateItineraryByIdForUser({
    itineraryId,
    userId,
    title,
    description,
    startDate,
    endDate,
    totalDays,
    status,
    estimatedBudget
  });

  const updated = await itinerariesRepository.getItineraryById(itineraryId);
  return itineraryRowToDto(updated, null);
}

export async function deleteItineraryForUser({ userId, itineraryId }) {
  await itinerariesRepository.deleteItineraryByIdForUser({ itineraryId, userId });
}

export async function saveAiItinerary({ userId, payload }) {
  const { title, description, startDate, endDate, budget, days } = payload;

  const safeStartDate = startDate || new Date().toISOString().split("T")[0];
  const safeEndDate = endDate || safeStartDate;

  const totalDays = daysBetweenInclusive(safeStartDate, safeEndDate);
  const isoStart = toIsoDate(safeStartDate);
  const isoEnd = toIsoDate(safeEndDate);

  const conn = await db.pool.getConnection();
  try {
    await conn.beginTransaction();

    const itinRes = await itinerariesRepository.insertItinerary(
      {
        userId,
        title: title || "Lịch trình AI",
        description: description || "Đã lưu từ gợi ý AI.",
        startDate: isoStart,
        endDate: isoEnd,
        totalDays,
        estimatedBudget: budget || null
      },
      conn
    );
    const itineraryId = itinRes.lastInsertRowid;

    if (days && Array.isArray(days)) {
      for (const day of days) {
        const d = new Date(isoStart);
        d.setDate(d.getDate() + ((day.dayNumber || 1) - 1));
        const dayDateStr = d.toISOString().split("T")[0];

        const dayRes = await itinerariesRepository.insertItineraryDay(
          {
            itineraryId,
            dayNumber: day.dayNumber || 1,
            date: dayDateStr
          },
          conn
        );
        const dayId = dayRes.lastInsertRowid;

        let orderIdx = 0;
        if (day.items && Array.isArray(day.items)) {
          for (const item of day.items) {
            await itinerariesRepository.insertItineraryItem(
              {
                dayId,
                destinationId: item.destinationId,
                orderIndex: orderIdx++,
                startTime: item.startTime || "08:00",
                endTime: item.endTime || "09:00",
                note: item.note || ""
              },
              conn
            );
          }
        }
      }
    }

    await conn.commit();
  } catch (err) {
    await conn.rollback();
    throw err;
  } finally {
    conn.release();
  }
}

/**
 * POST /itineraries/create-from-option persistence (non-transactional db.run), after route field validation.
 *
 * @param {{ userId: number, payload: Record<string, unknown> }} params
 * @returns {Promise<
 *   | { ok: false; reason: "no_mapped_destinations"; optionId: unknown; unresolved: unknown[] }
 *   | { ok: false; reason: "invalid_dates" }
 *   | {
 *       ok: true;
 *       data: {
 *         id: number;
 *         itineraryId: number;
 *         optionId: unknown;
 *         selectedCount: number;
 *         unresolved: unknown[];
 *       };
 *     }
 * >}
 */
export async function createItineraryFromAiOption({ userId, payload }) {
  const {
    title,
    description,
    startDate,
    endDate,
    estimatedBudget,
    budget,
    optionId,
    days
  } = payload;

  const selectedDestinations = flattenSelectedOptionDays(days);

  const resolved = await resolveDestinationIdsFromSelection(selectedDestinations);
  const destinationIds = resolved.destinationIds;
  const unresolved = resolved.unresolved;

  if (destinationIds.length === 0) {
    return {
      ok: false,
      reason: "no_mapped_destinations",
      optionId: optionId ?? null,
      unresolved
    };
  }

  const start = new Date(startDate);
  const end = new Date(endDate);

  if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) {
    return { ok: false, reason: "invalid_dates" };
  }

  const totalDays = Math.max(1, Math.floor((end - start) / (1000 * 60 * 60 * 24)) + 1);

  const finalBudget = estimatedBudget ?? budget ?? null;

  const itineraryInfo = await db.run(
    `
      INSERT INTO itineraries
      (user_id, title, description, start_date, end_date, total_days, status, estimated_budget)
      VALUES (?, ?, ?, ?, ?, ?, 'planned', ?)
      `,
    [userId, title, description ?? null, startDate, endDate, totalDays, finalBudget]
  );

  const itineraryId = Number(itineraryInfo.lastInsertRowid);
  const dayIdByNumber = new Map();

  for (let dayNumber = 1; dayNumber <= totalDays; dayNumber++) {
    const date = new Date(start);
    date.setDate(start.getDate() + dayNumber - 1);

    const dateText = date.toISOString().slice(0, 10);

    const dayInfo = await db.run(
      `
        INSERT INTO itinerary_days (itinerary_id, day_number, date)
        VALUES (?, ?, ?)
        `,
      [itineraryId, dayNumber, dateText]
    );

    dayIdByNumber.set(dayNumber, Number(dayInfo.lastInsertRowid));
  }

  const destinationIdByRawPlaceId = new Map();

  for (const item of selectedDestinations) {
    const directId = item?.destinationId ?? item?.destination_id;
    const rawPlaceId =
      item?.rawPlaceId ?? item?.raw_place_id ?? item?.placeId ?? item?.place_id;

    if (
      directId !== null &&
      directId !== undefined &&
      Number.isInteger(Number(directId)) &&
      Number(directId) > 0
    ) {
      if (rawPlaceId) {
        destinationIdByRawPlaceId.set(String(rawPlaceId), Number(directId));
      }
      continue;
    }

    if (!rawPlaceId) continue;

    const row = await aiRepository.getDestinationIdByRagPlaceId(rawPlaceId);

    if (row?.destination_id) {
      destinationIdByRawPlaceId.set(String(rawPlaceId), Number(row.destination_id));
    }
  }

  const timeSlots = [
    ["08:00", "10:00"],
    ["10:30", "12:00"],
    ["14:00", "16:00"],
    ["16:30", "18:00"]
  ];

  let insertedCount = 0;

  for (const day of days) {
    const dayNumber = Number(day?.dayNumber || 1);
    const dayId = dayIdByNumber.get(dayNumber);

    if (!dayId) continue;

    const items = Array.isArray(day?.items) ? day.items : [];

    for (let index = 0; index < items.length; index++) {
      const item = items[index];
      const rawPlaceId =
        item?.rawPlaceId ?? item?.raw_place_id ?? item?.placeId ?? item?.place_id;

      const directId = item?.destinationId ?? item?.destination_id;

      let destinationId = null;

      if (
        directId !== null &&
        directId !== undefined &&
        Number.isInteger(Number(directId)) &&
        Number(directId) > 0
      ) {
        destinationId = Number(directId);
      } else if (rawPlaceId) {
        destinationId = destinationIdByRawPlaceId.get(String(rawPlaceId));
      }

      if (!destinationId) continue;

      const slot = timeSlots[index % timeSlots.length];

      await db.run(
        `
          INSERT INTO itinerary_items
          (day_id, destination_id, start_time, end_time, note, order_index)
          VALUES (?, ?, ?, ?, ?, ?)
          `,
        [
          dayId,
          destinationId,
          item?.startTime || slot[0],
          item?.endTime || slot[1],
          item?.reason || "Được chọn từ AI tour",
          index + 1
        ]
      );

      insertedCount++;
    }
  }

  return {
    ok: true,
    data: {
      id: itineraryId,
      itineraryId,
      optionId: optionId ?? null,
      selectedCount: insertedCount,
      unresolved
    }
  };
}

/**
 * POST /itineraries/create-from-selection persistence (non-transactional db.run), after route field validation.
 *
 * @param {{ userId: number, payload: Record<string, unknown> }} params
 * @returns {Promise<
 *   | {
 *       ok: false;
 *       reason: "no_mapped_destinations";
 *       receivedSelectedDestinations: unknown;
 *       receivedSelectedDestinationIds: unknown;
 *       unresolved: unknown[];
 *     }
 *   | { ok: false; reason: "invalid_dates" }
 *   | {
 *       ok: true;
 *       data: {
 *         id: unknown;
 *         itineraryId: unknown;
 *         selectedCount: number;
 *         destinationIds: number[];
 *         unresolved: unknown[];
 *       };
 *     }
 * >}
 */
export async function createItineraryFromAiSelection({ userId, payload }) {
  const {
    title,
    description,
    startDate,
    endDate,
    estimatedBudget,
    budget,
    selectedDestinations,
    selectedDestinationIds
  } = payload;

  let destinationIds = [];
  let unresolved = [];

  if (Array.isArray(selectedDestinationIds) && selectedDestinationIds.length > 0) {
    destinationIds = selectedDestinationIds
      .map((id) => Number(id))
      .filter((id) => Number.isInteger(id) && id > 0);
  } else if (Array.isArray(selectedDestinations) && selectedDestinations.length > 0) {
    const resolved = await resolveDestinationIdsFromSelection(selectedDestinations);
    destinationIds = resolved.destinationIds;
    unresolved = resolved.unresolved;
  }

  if (destinationIds.length === 0) {
    return {
      ok: false,
      reason: "no_mapped_destinations",
      receivedSelectedDestinations: selectedDestinations ?? null,
      receivedSelectedDestinationIds: selectedDestinationIds ?? null,
      unresolved
    };
  }

  const start = new Date(startDate);
  const end = new Date(endDate);

  if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) {
    return { ok: false, reason: "invalid_dates" };
  }

  const totalDays = Math.max(1, Math.floor((end - start) / (1000 * 60 * 60 * 24)) + 1);

  const finalBudget = estimatedBudget ?? budget ?? null;

  const itineraryInfo = await db.run(
    `
      INSERT INTO itineraries
      (user_id, title, description, start_date, end_date, total_days, status, estimated_budget)
      VALUES (?, ?, ?, ?, ?, ?, 'planned', ?)
      `,
    [userId, title, description ?? null, startDate, endDate, totalDays, finalBudget]
  );

  const itineraryId = itineraryInfo.lastInsertRowid;
  const dayIds = [];

  for (let dayNumber = 1; dayNumber <= totalDays; dayNumber++) {
    const date = new Date(start);
    date.setDate(start.getDate() + dayNumber - 1);

    const dateText = date.toISOString().slice(0, 10);

    const dayInfo = await db.run(
      `
        INSERT INTO itinerary_days (itinerary_id, day_number, date)
        VALUES (?, ?, ?)
        `,
      [itineraryId, dayNumber, dateText]
    );

    dayIds.push(dayInfo.lastInsertRowid);
  }

  const timeSlots = [
    ["08:00", "10:00"],
    ["10:30", "12:00"],
    ["14:00", "16:00"],
    ["16:30", "18:00"]
  ];

  for (let i = 0; i < destinationIds.length; i++) {
    const dayIndex = i % totalDays;
    const orderIndex = Math.floor(i / totalDays);
    const slot = timeSlots[orderIndex % timeSlots.length];

    await db.run(
      `
        INSERT INTO itinerary_items
        (day_id, destination_id, start_time, end_time, note, order_index)
        VALUES (?, ?, ?, ?, ?, ?)
        `,
      [
        dayIds[dayIndex],
        destinationIds[i],
        slot[0],
        slot[1],
        "Được chọn từ AI gợi ý",
        orderIndex + 1
      ]
    );
  }

  return {
    ok: true,
    data: {
      id: itineraryId,
      itineraryId,
      selectedCount: destinationIds.length,
      destinationIds,
      unresolved
    }
  };
}
