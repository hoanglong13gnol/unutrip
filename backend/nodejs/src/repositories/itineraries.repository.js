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
      JOIN app_places d2 ON d2.id = ii.destination_id
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

export async function getItineraryDayByIdForItinerary({ dayId, itineraryId }) {
  return db.get("SELECT * FROM itinerary_days WHERE id = ? AND itinerary_id = ?", [dayId, itineraryId]);
}

export async function getItineraryItemJoinDayById(itemId) {
  return db.get(
    `
      SELECT ii.*, idy.itinerary_id AS itinerary_id
      FROM itinerary_items ii
      JOIN itinerary_days idy ON idy.id = ii.day_id
      WHERE ii.id = ?
    `,
    [itemId]
  );
}

export async function updateItineraryItemById({
  itemId,
  dayId,
  destinationId,
  startTime,
  endTime,
  note,
  orderIndex
}) {
  await db.run(
    `
      UPDATE itinerary_items
      SET day_id = ?, destination_id = ?, start_time = ?, end_time = ?, note = ?, order_index = ?
      WHERE id = ?
    `,
    [dayId, destinationId, startTime, endTime, note ?? null, orderIndex, itemId]
  );
}

export async function deleteItineraryItemById(itemId) {
  await db.run("DELETE FROM itinerary_items WHERE id = ?", [itemId]);
}

export async function listItineraryDaysByItineraryIdConn(itineraryId, conn) {
  const runner = getRunner(conn);
  const sql = "SELECT * FROM itinerary_days WHERE itinerary_id = ? ORDER BY day_number ASC";
  if (runner) {
    const [rows] = await runner.query(sql, [itineraryId]);
    return rows;
  }
  return db.query(sql, [itineraryId]);
}

export async function deleteItineraryDayByIdForItinerary({ dayId, itineraryId }, conn) {
  const runner = getRunner(conn);
  const sql = "DELETE FROM itinerary_days WHERE id = ? AND itinerary_id = ?";
  const params = [dayId, itineraryId];
  if (runner) {
    await runner.query(sql, params);
    return;
  }
  await db.run(sql, params);
}

export async function updateItineraryDayNumberAndDate({ dayId, dayNumber, date }, conn) {
  const runner = getRunner(conn);
  const sql = "UPDATE itinerary_days SET day_number = ?, date = ? WHERE id = ?";
  const params = [dayNumber, date, dayId];
  if (runner) {
    await runner.query(sql, params);
    return;
  }
  await db.run(sql, params);
}

export async function updateItineraryEndAndTotalByUser({ itineraryId, userId, endDate, totalDays }, conn) {
  const runner = getRunner(conn);
  const sql =
    "UPDATE itineraries SET end_date = ?, total_days = ? WHERE id = ? AND user_id = ?";
  const params = [endDate, totalDays, itineraryId, userId];
  if (runner) {
    await runner.query(sql, params);
    return;
  }
  await db.run(sql, params);
}
