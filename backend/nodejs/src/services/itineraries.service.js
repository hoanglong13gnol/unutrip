import { db } from "../db.js";
import { daysBetweenInclusive, toIsoDate } from "../utils.js";
import * as itinerariesRepository from "../repositories/itineraries.repository.js";
import { itineraryRowToDto, toDestinationDto } from "../routes/helpers.js";

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
