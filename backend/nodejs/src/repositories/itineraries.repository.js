import { db } from "../db.js";

function getRunner(conn) {
  if (!conn) return null;
  return {
    query(sql, params) {
      return conn.execute(sql, params);
    }
  };
}

export async function listItinerariesByUserId(userId) {
  return db.query(
    `
      SELECT *
      FROM itineraries
      WHERE user_id = ?
      ORDER BY created_at DESC, id DESC
    `,
    [userId]
  );
}

export async function getItineraryByIdForUser({ itineraryId, userId }) {
  return db.get("SELECT * FROM itineraries WHERE id = ? AND user_id = ?", [itineraryId, userId]);
}

export async function getItineraryById(itineraryId) {
  return db.get("SELECT * FROM itineraries WHERE id = ?", [itineraryId]);
}

export async function listItineraryDaysByItineraryId(itineraryId) {
  return db.query("SELECT * FROM itinerary_days WHERE itinerary_id = ? ORDER BY day_number ASC", [itineraryId]);
}

export async function listItineraryItemsWithDestinationByDayId(dayId) {
  return db.query(
    `
      SELECT ii.*, d2.*
      FROM itinerary_items ii
      JOIN destinations d2 ON d2.id = ii.destination_id
      WHERE ii.day_id = ?
      ORDER BY ii.order_index ASC
    `,
    [dayId]
  );
}

export async function insertItinerary(
  { userId, title, description, startDate, endDate, totalDays, estimatedBudget },
  conn
) {
  const runner = getRunner(conn);
  if (runner) {
    const [result] = await runner.query(
      `
        INSERT INTO itineraries (user_id, title, description, start_date, end_date, total_days, status, estimated_budget)
        VALUES (?, ?, ?, ?, ?, ?, 'planned', ?)
      `,
      [userId, title, description ?? null, startDate, endDate, totalDays, estimatedBudget]
    );
    return { lastInsertRowid: result.insertId };
  }

  return db.run(
    `
      INSERT INTO itineraries (user_id, title, description, start_date, end_date, total_days, status, estimated_budget)
      VALUES (?, ?, ?, ?, ?, ?, 'planned', ?)
    `,
    [userId, title, description ?? null, startDate, endDate, totalDays, estimatedBudget]
  );
}

export async function insertItineraryDay({ itineraryId, dayNumber, date }, conn) {
  const runner = getRunner(conn);
  if (runner) {
    const [result] = await runner.query(
      `
        INSERT INTO itinerary_days (itinerary_id, day_number, date)
        VALUES (?, ?, ?)
      `,
      [itineraryId, dayNumber, date]
    );
    return { lastInsertRowid: result.insertId };
  }

  return db.run("INSERT INTO itinerary_days (itinerary_id, day_number, date) VALUES (?, ?, ?)", [
    itineraryId,
    dayNumber,
    date
  ]);
}

export async function insertItineraryItem({ dayId, destinationId, startTime, endTime, note, orderIndex }, conn) {
  const runner = getRunner(conn);
  if (runner) {
    await runner.query(
      `
        INSERT INTO itinerary_items (day_id, destination_id, start_time, end_time, note, order_index)
        VALUES (?, ?, ?, ?, ?, ?)
      `,
      [dayId, destinationId, startTime, endTime, note, orderIndex]
    );
    return;
  }

  await db.run(
    `
      INSERT INTO itinerary_items (day_id, destination_id, start_time, end_time, note, order_index)
      VALUES (?, ?, ?, ?, ?, ?)
    `,
    [dayId, destinationId, startTime, endTime, note, orderIndex]
  );
}

export async function getFirstItineraryDayId(itineraryId) {
  const row = await db.get("SELECT id FROM itinerary_days WHERE itinerary_id = ? ORDER BY day_number ASC LIMIT 1", [
    itineraryId
  ]);
  return row?.id ?? null;
}

export async function getMaxOrderIndexByDayId(dayId) {
  const row = await db.get("SELECT MAX(order_index) as max_idx FROM itinerary_items WHERE day_id = ?", [dayId]);
  return row?.max_idx ?? null;
}

export async function updateItineraryByIdForUser({
  itineraryId,
  userId,
  title,
  description,
  startDate,
  endDate,
  totalDays,
  status,
  estimatedBudget
}) {
  await db.run(
    `
      UPDATE itineraries
      SET title = ?, description = ?, start_date = ?, end_date = ?, total_days = ?, status = COALESCE(?, status), estimated_budget = ?
      WHERE id = ? AND user_id = ?
    `,
    [title, description ?? null, startDate, endDate, totalDays, status ?? null, estimatedBudget, itineraryId, userId]
  );
}

export async function deleteItineraryByIdForUser({ itineraryId, userId }) {
  await db.run("DELETE FROM itineraries WHERE id = ? AND user_id = ?", [itineraryId, userId]);
}
