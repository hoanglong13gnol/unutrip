import { daysBetweenInclusive, toIsoDate } from "../utils.js";
import * as itinerariesRepository from "../repositories/itineraries.repository.js";
import * as placeIdMapRepository from "../repositories/placeIdMap.repository.js";
import { withTransaction } from "../shared/db/withTransaction.js";
import { DEFAULT_AI_ITINERARY_TIME_SLOTS } from "../shared/utils/timeSlots.js";
import {
  attachDestinationImages,
  toDestinationDto
} from "../shared/dto/destinationDto.js";
import {
  flattenSelectedOptionDays,
  itineraryRowToDto,
  resolveDestinationIdsFromSelection
} from "../shared/dto/itineraryDto.js";

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
    const attachRows = items.map((row) => ({ ...row, id: row.destination_id }));
    const attachedRows = await attachDestinationImages(attachRows);
    const itemsWithImages = items.map((row, idx) => ({
      ...row,
      images_from_table: attachedRows[idx]?.images_from_table
    }));
    dayDtos.push({
      id: d.id,
      itineraryId: d.itinerary_id,
      dayNumber: d.day_number,
      date: d.date,
      items: itemsWithImages.map((i) => ({
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

  const itineraryId = await withTransaction(async (conn) => {
    const info = await itinerariesRepository.insertItinerary(
      {
        userId,
        title,
        description,
        startDate: toIsoDate(startDate),
        endDate: toIsoDate(endDate),
        totalDays,
        estimatedBudget
      },
      conn
    );

    const newItineraryId = Number(info.lastInsertRowid);
    const destIds = Array.isArray(destinationIds) ? destinationIds : [];

    for (let d = 0; d < totalDays; d++) {
      const date = new Date(toIsoDate(startDate));
      date.setDate(date.getDate() + d);
      const dayInfo = await itinerariesRepository.insertItineraryDay(
        {
          itineraryId: newItineraryId,
          dayNumber: d + 1,
          date: toIsoDate(date)
        },
        conn
      );
      const dayId = Number(dayInfo.lastInsertRowid);

      const chunk = destIds.slice(d * 2, d * 2 + 2);
      for (const [idx, destId] of chunk.entries()) {
        await itinerariesRepository.insertItineraryItem(
          {
            dayId,
            destinationId: destId,
            startTime: idx === 0 ? "09:00" : "14:00",
            endTime: idx === 0 ? "12:00" : "17:00",
            note: null,
            orderIndex: idx
          },
          conn
        );
      }
    }

    return newItineraryId;
  });

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
  } else {
    const dayRow = await itinerariesRepository.getItineraryDayByIdForItinerary({
      dayId: targetDayId,
      itineraryId
    });
    if (!dayRow) {
      return { ok: false, reason: "invalid_day" };
    }
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

export async function updateItineraryItemForUser({ userId, itineraryId, itemId, payload }) {
  const it = await itinerariesRepository.getItineraryByIdForUser({ itineraryId, userId });
  if (!it) {
    return { ok: false, reason: "not_authorized" };
  }

  const row = await itinerariesRepository.getItineraryItemJoinDayById(itemId);
  if (!row || Number(row.itinerary_id) !== Number(itineraryId)) {
    return { ok: false, reason: "not_found" };
  }

  const nextDayId = payload.dayId !== undefined ? Number(payload.dayId) : Number(row.day_id);
  if (nextDayId !== Number(row.day_id)) {
    const dayRow = await itinerariesRepository.getItineraryDayByIdForItinerary({
      dayId: nextDayId,
      itineraryId
    });
    if (!dayRow) {
      return { ok: false, reason: "invalid_day" };
    }
  }

  const nextDestinationId =
    payload.destinationId !== undefined ? Number(payload.destinationId) : Number(row.destination_id);

  const nextStart = payload.startTime !== undefined ? payload.startTime : row.start_time;
  const nextEnd = payload.endTime !== undefined ? payload.endTime : row.end_time;
  const nextNote = payload.note !== undefined ? payload.note : row.note;
  const nextOrder =
    payload.orderIndex !== undefined ? Number(payload.orderIndex) : Number(row.order_index);

  if (!nextDestinationId) {
    return { ok: false, reason: "missing_destination_id" };
  }

  await itinerariesRepository.updateItineraryItemById({
    itemId,
    dayId: nextDayId,
    destinationId: nextDestinationId,
    startTime: nextStart,
    endTime: nextEnd,
    note: nextNote,
    orderIndex: nextOrder
  });

  return { ok: true };
}

function plusOneCalendarDay(isoDate) {
  const base = toIsoDate(isoDate);
  const d = new Date(base);
  d.setDate(d.getDate() + 1);
  return d.toISOString().slice(0, 10);
}

function dateOffsetFromStart(startIso, indexZeroBased) {
  const d = new Date(toIsoDate(startIso));
  d.setDate(d.getDate() + indexZeroBased);
  return d.toISOString().slice(0, 10);
}

export async function addItineraryDayForUser({ userId, itineraryId }) {
  const it = await itinerariesRepository.getItineraryByIdForUser({ itineraryId, userId });
  if (!it) {
    return { ok: false, reason: "not_authorized" };
  }

  await withTransaction(async (conn) => {
    const days = await itinerariesRepository.listItineraryDaysByItineraryIdConn(itineraryId, conn);
    const nextNum = days.length + 1;
    const newDate =
      days.length === 0
        ? toIsoDate(it.start_date)
        : plusOneCalendarDay(days[days.length - 1].date);

    await itinerariesRepository.insertItineraryDay(
      { itineraryId, dayNumber: nextNum, date: newDate },
      conn
    );
    await itinerariesRepository.updateItineraryEndAndTotalByUser(
      { itineraryId, userId, endDate: newDate, totalDays: nextNum },
      conn
    );
  });

  return { ok: true };
}

export async function deleteItineraryDayForUser({ userId, itineraryId, dayId }) {
  const it = await itinerariesRepository.getItineraryByIdForUser({ itineraryId, userId });
  if (!it) {
    return { ok: false, reason: "not_authorized" };
  }

  const dayRow = await itinerariesRepository.getItineraryDayByIdForItinerary({
    dayId,
    itineraryId
  });
  if (!dayRow) {
    return { ok: false, reason: "not_found" };
  }

  const daysBefore = await itinerariesRepository.listItineraryDaysByItineraryId(itineraryId);
  if (daysBefore.length <= 1) {
    return { ok: false, reason: "last_day" };
  }

  await withTransaction(async (conn) => {
    await itinerariesRepository.deleteItineraryDayByIdForItinerary({ dayId, itineraryId }, conn);
    const remaining = await itinerariesRepository.listItineraryDaysByItineraryIdConn(
      itineraryId,
      conn
    );
    const startIso = toIsoDate(it.start_date);
    for (let i = 0; i < remaining.length; i += 1) {
      const row = remaining[i];
      const newNum = i + 1;
      const newDate = dateOffsetFromStart(startIso, i);
      await itinerariesRepository.updateItineraryDayNumberAndDate(
        { dayId: row.id, dayNumber: newNum, date: newDate },
        conn
      );
    }
    const newTotal = remaining.length;
    const newEnd =
      newTotal === 0 ? startIso : dateOffsetFromStart(startIso, newTotal - 1);
    await itinerariesRepository.updateItineraryEndAndTotalByUser(
      { itineraryId, userId, endDate: newEnd, totalDays: newTotal },
      conn
    );
  });

  return { ok: true };
}

export async function deleteItineraryItemForUser({ userId, itineraryId, itemId }) {
  const it = await itinerariesRepository.getItineraryByIdForUser({ itineraryId, userId });
  if (!it) {
    return { ok: false, reason: "not_authorized" };
  }

  const row = await itinerariesRepository.getItineraryItemJoinDayById(itemId);
  if (!row || Number(row.itinerary_id) !== Number(itineraryId)) {
    return { ok: false, reason: "not_found" };
  }

  await itinerariesRepository.deleteItineraryItemById(itemId);
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

  await withTransaction(async (conn) => {
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
  });
}

/**
 * POST /itineraries/create-from-option persistence (wrapped in `withTransaction` in Phase 3), after route field validation.
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

    const destinationId = await placeIdMapRepository.getDestinationIdByRagPlaceId(rawPlaceId);

    if (destinationId) {
      destinationIdByRawPlaceId.set(String(rawPlaceId), Number(destinationId));
    }
  }

  const timeSlots = DEFAULT_AI_ITINERARY_TIME_SLOTS;

  const { itineraryId, insertedCount } = await withTransaction(async (conn) => {
    const itineraryInfo = await itinerariesRepository.insertItinerary(
      {
        userId,
        title,
        description: description ?? null,
        startDate,
        endDate,
        totalDays,
        estimatedBudget: finalBudget
      },
      conn
    );

    const newItineraryId = Number(itineraryInfo.lastInsertRowid);
    const dayIdByNumber = new Map();

    for (let dayNumber = 1; dayNumber <= totalDays; dayNumber++) {
      const date = new Date(start);
      date.setDate(start.getDate() + dayNumber - 1);

      const dateText = date.toISOString().slice(0, 10);

      const dayInfo = await itinerariesRepository.insertItineraryDay(
        {
          itineraryId: newItineraryId,
          dayNumber,
          date: dateText
        },
        conn
      );

      dayIdByNumber.set(dayNumber, Number(dayInfo.lastInsertRowid));
    }

    let inserted = 0;

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

        await itinerariesRepository.insertItineraryItem(
          {
            dayId,
            destinationId,
            startTime: item?.startTime || slot[0],
            endTime: item?.endTime || slot[1],
            note: item?.reason || "Được chọn từ AI tour",
            orderIndex: index + 1
          },
          conn
        );

        inserted++;
      }
    }

    return { itineraryId: newItineraryId, insertedCount: inserted };
  });

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
 * POST /itineraries/create-from-selection persistence (wrapped in `withTransaction` in Phase 3), after route field validation.
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

  const timeSlots = DEFAULT_AI_ITINERARY_TIME_SLOTS;

  const itineraryId = await withTransaction(async (conn) => {
    const itineraryInfo = await itinerariesRepository.insertItinerary(
      {
        userId,
        title,
        description: description ?? null,
        startDate,
        endDate,
        totalDays,
        estimatedBudget: finalBudget
      },
      conn
    );

    const newItineraryId = itineraryInfo.lastInsertRowid;
    const dayIds = [];

    for (let dayNumber = 1; dayNumber <= totalDays; dayNumber++) {
      const date = new Date(start);
      date.setDate(start.getDate() + dayNumber - 1);

      const dateText = date.toISOString().slice(0, 10);

      const dayInfo = await itinerariesRepository.insertItineraryDay(
        {
          itineraryId: newItineraryId,
          dayNumber,
          date: dateText
        },
        conn
      );

      dayIds.push(dayInfo.lastInsertRowid);
    }

    for (let i = 0; i < destinationIds.length; i++) {
      const dayIndex = i % totalDays;
      const orderIndex = Math.floor(i / totalDays);
      const slot = timeSlots[orderIndex % timeSlots.length];

      await itinerariesRepository.insertItineraryItem(
        {
          dayId: dayIds[dayIndex],
          destinationId: destinationIds[i],
          startTime: slot[0],
          endTime: slot[1],
          note: "Được chọn từ AI gợi ý",
          orderIndex: orderIndex + 1
        },
        conn
      );
    }

    return newItineraryId;
  });

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

/**
 * POST /ai/suggest-itinerary persistence (Phase 3 work item A).
 *
 * Owns the transactional INSERTs that the controller previously did inline:
 * one row in `itineraries`, N rows in `itinerary_days`, and M rows in
 * `itinerary_items`. Wrapped in a single `withTransaction` boundary so a
 * mid-flight failure cannot leave partial rows behind. Date parsing,
 * AI-result generation, and `invalid_ai_json` handling stay in the
 * controller — only persistence lives here.
 *
 * @param {{
 *   userId: number,
 *   aiResult: { title?: string, description?: string, days?: Array<{ dayNumber?: number, items?: Array<{ destinationId: number, startTime?: string, endTime?: string, note?: string }> }> },
 *   isoStart: string,
 *   isoEnd: string,
 *   totalDays: number,
 *   budget?: number | null
 * }} params
 * @returns {Promise<{
 *   id: number,
 *   userId: number,
 *   title: string | undefined,
 *   description: string | undefined,
 *   startDate: string,
 *   endDate: string,
 *   totalDays: number,
 *   status: "planned",
 *   estimatedBudget: number | null
 * }>} The `newItin` object the controller returns to the Android client.
 */
export async function persistAiSuggestedItinerary({
  userId,
  aiResult,
  isoStart,
  isoEnd,
  totalDays,
  budget
}) {
  const itineraryId = await withTransaction(async (conn) => {
    const itinRes = await itinerariesRepository.insertItinerary(
      {
        userId,
        title: aiResult.title || "Lịch trình AI tạo",
        description: aiResult.description || "Tạo bởi Hướng dẫn viên du lịch ảo.",
        startDate: isoStart,
        endDate: isoEnd,
        totalDays,
        estimatedBudget: budget || null
      },
      conn
    );
    const newItineraryId = itinRes.lastInsertRowid;

    if (aiResult.days && Array.isArray(aiResult.days)) {
      for (const day of aiResult.days) {
        const dayDate = new Date(isoStart);
        dayDate.setDate(dayDate.getDate() + ((day.dayNumber || 1) - 1));
        const dayDateStr = toIsoDate(dayDate.toISOString().split("T")[0]);

        const dayRes = await itinerariesRepository.insertItineraryDay(
          {
            itineraryId: newItineraryId,
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

    return newItineraryId;
  });

  return {
    id: itineraryId,
    userId,
    title: aiResult.title,
    description: aiResult.description,
    startDate: isoStart,
    endDate: isoEnd,
    totalDays,
    status: "planned",
    estimatedBudget: budget || null
  };
}
