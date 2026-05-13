import { z } from "zod";
import { db } from "../db.js";
import { apiOk, daysBetweenInclusive, toIsoDate } from "../utils.js";
import { authMiddleware } from "../auth.js";
import {
  itineraryRowToDto,
  toDestinationDto
} from "./helpers.js";

export function registerItineraryRoutes(router) {
  router.get("/itineraries", authMiddleware, async (req, res) => {
    const rows = await db.query(
      `
      SELECT *
      FROM itineraries
      WHERE user_id = ?
      ORDER BY created_at DESC, id DESC
    `,
      [req.user.userId]
    );

    const data = rows.map((r) => itineraryRowToDto(r, null));
    return res.json({ success: true, data });
  });

  router.get("/itineraries/:id", authMiddleware, async (req, res) => {
    const id = Number(req.params.id);
    const it = await db.get("SELECT * FROM itineraries WHERE id = ? AND user_id = ?", [
      id,
      req.user.userId
    ]);
    if (!it) return res.status(404).json({ success: false, message: "Not found", data: null });

    const days = await db.query("SELECT * FROM itinerary_days WHERE itinerary_id = ? ORDER BY day_number ASC", [
      id
    ]);
    const dayDtos = [];
    for (const d of days) {
      const items = await db.query(
        `
        SELECT ii.*, d2.*
        FROM itinerary_items ii
        JOIN destinations d2 ON d2.id = ii.destination_id
        WHERE ii.day_id = ?
        ORDER BY ii.order_index ASC
      `,
        [d.id]
      );
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

    return res.json(apiOk(itineraryRowToDto(it, dayDtos), "OK"));
  });

  router.post("/itineraries", authMiddleware, async (req, res) => {
    const schema = z.object({
      title: z.string().min(1),
      description: z.string().optional().nullable(),
      startDate: z.string().min(8),
      endDate: z.string().min(8),
      estimatedBudget: z.number().optional().nullable(),
      budget: z.number().optional().nullable(),
      destinationIds: z.array(z.number().int()).optional().nullable()
    });
    const parsed = schema.safeParse(req.body);
    if (!parsed.success) return res.status(400).json({ success: false, message: "Invalid payload", data: null });

    const { title, description, startDate, endDate, destinationIds } = parsed.data;
    const estimatedBudget = parsed.data.estimatedBudget ?? parsed.data.budget ?? null;
    const totalDays = daysBetweenInclusive(startDate, endDate);

    const info = await db.run(
      `
        INSERT INTO itineraries (user_id, title, description, start_date, end_date, total_days, status, estimated_budget)
        VALUES (?, ?, ?, ?, ?, ?, 'planned', ?)
      `,
      [
        req.user.userId,
        title,
        description ?? null,
        toIsoDate(startDate),
        toIsoDate(endDate),
        totalDays,
        estimatedBudget
      ]
    );

    const itineraryId = Number(info.lastInsertRowid);
    const destIds = Array.isArray(destinationIds) ? destinationIds : [];

    for (let d = 0; d < totalDays; d++) {
      const date = new Date(toIsoDate(startDate));
      date.setDate(date.getDate() + d);
      const dayInfo = await db.run("INSERT INTO itinerary_days (itinerary_id, day_number, date) VALUES (?, ?, ?)", [
        itineraryId,
        d + 1,
        toIsoDate(date)
      ]);
      const dayId = Number(dayInfo.lastInsertRowid);

      const chunk = destIds.slice(d * 2, d * 2 + 2);
      for (const [idx, destId] of chunk.entries()) {
        await db.run(
          `
          INSERT INTO itinerary_items (day_id, destination_id, start_time, end_time, note, order_index)
          VALUES (?, ?, ?, ?, ?, ?)
        `,
          [dayId, destId, idx === 0 ? "09:00" : "14:00", idx === 0 ? "12:00" : "17:00", null, idx]
        );
      }
    }

    const it = await db.get("SELECT * FROM itineraries WHERE id = ?", [itineraryId]);
    return res.json(apiOk(itineraryRowToDto(it, null), "OK"));
  });

  router.post("/itineraries/:id/items", authMiddleware, async (req, res) => {
    try {
      const itineraryId = Number(req.params.id);
      const { destinationId, dayId, startTime, endTime, note } = req.body;

      if (!destinationId) {
        return res.status(400).json({ success: false, message: "Missing destinationId" });
      }

      const it = await db.get("SELECT id FROM itineraries WHERE id = ? AND user_id = ?", [
        itineraryId,
        req.user.userId
      ]);
      if (!it) return res.status(403).json({ success: false, message: "Not authorized or not found" });

      let targetDayId = dayId;
      if (!targetDayId) {
        const firstDay = await db.get(
          "SELECT id FROM itinerary_days WHERE itinerary_id = ? ORDER BY day_number ASC LIMIT 1",
          [itineraryId]
        );
        if (!firstDay) return res.status(400).json({ success: false, message: "No days in itinerary" });
        targetDayId = firstDay.id;
      }

      const maxRow = await db.get("SELECT MAX(order_index) as max_idx FROM itinerary_items WHERE day_id = ?", [
        targetDayId
      ]);
      const nextIdx = (maxRow?.max_idx ?? -1) + 1;

      await db.run(
        `
        INSERT INTO itinerary_items (day_id, destination_id, order_index, start_time, end_time, note)
        VALUES (?, ?, ?, ?, ?, ?)
      `,
        [targetDayId, destinationId, nextIdx, startTime || "09:00", endTime || "10:00", note || ""]
      );

      return res.json({ success: true, message: "Đã thêm vào lịch trình" });
    } catch (e) {
      console.error(e);
      return res.status(500).json({ success: false, message: "Server Error" });
    }
  });

  router.put("/itineraries/:id", authMiddleware, async (req, res) => {
    const id = Number(req.params.id);
    const it = await db.get("SELECT * FROM itineraries WHERE id = ? AND user_id = ?", [id, req.user.userId]);
    if (!it) return res.status(404).json({ success: false, message: "Not found", data: null });

    const schema = z.object({
      id: z.number().int().optional(),
      userId: z.number().int().optional(),
      title: z.string().min(1),
      description: z.string().optional().nullable(),
      startDate: z.string().min(8),
      endDate: z.string().min(8),
      totalDays: z.number().int().optional(),
      status: z.string().optional(),
      estimatedBudget: z.number().optional().nullable(),
      createdAt: z.string().optional()
    });
    const parsed = schema.safeParse(req.body);
    if (!parsed.success) return res.status(400).json({ success: false, message: "Invalid payload", data: null });

    const totalDays = daysBetweenInclusive(parsed.data.startDate, parsed.data.endDate);
    await db.run(
      `
      UPDATE itineraries
      SET title = ?, description = ?, start_date = ?, end_date = ?, total_days = ?, status = COALESCE(?, status), estimated_budget = ?
      WHERE id = ? AND user_id = ?
    `,
      [
        parsed.data.title,
        parsed.data.description ?? null,
        toIsoDate(parsed.data.startDate),
        toIsoDate(parsed.data.endDate),
        totalDays,
        parsed.data.status ?? null,
        parsed.data.estimatedBudget ?? null,
        id,
        req.user.userId
      ]
    );

    const updated = await db.get("SELECT * FROM itineraries WHERE id = ?", [id]);
    return res.json(apiOk(itineraryRowToDto(updated, null), "OK"));
  });

  router.delete("/itineraries/:id", authMiddleware, async (req, res) => {
    const id = Number(req.params.id);
    await db.run("DELETE FROM itineraries WHERE id = ? AND user_id = ?", [id, req.user.userId]);
    return res.json(apiOk(null, "OK"));
  });

  router.post("/itineraries/save-ai", authMiddleware, async (req, res) => {
    try {
      console.log("[AI] Save AI Itinerary Request:", JSON.stringify(req.body).substring(0, 500));
      const { title, description, startDate, endDate, budget, days } = req.body;

      const safeStartDate = startDate || new Date().toISOString().split("T")[0];
      const safeEndDate = endDate || safeStartDate;

      const totalDays = daysBetweenInclusive(safeStartDate, safeEndDate);
      const isoStart = toIsoDate(safeStartDate);
      const isoEnd = toIsoDate(safeEndDate);

      const conn = await db.pool.getConnection();
      try {
        await conn.beginTransaction();

        const [itinRes] = await conn.execute(
          `
          INSERT INTO itineraries (user_id, title, description, start_date, end_date, total_days, status, estimated_budget)
          VALUES (?, ?, ?, ?, ?, ?, 'planned', ?)
        `,
          [
            req.user.userId,
            title || "Lịch trình AI",
            description || "Đã lưu từ gợi ý AI.",
            isoStart,
            isoEnd,
            totalDays,
            budget || null
          ]
        );
        const itineraryId = itinRes.insertId;

        if (days && Array.isArray(days)) {
          for (const day of days) {
            const d = new Date(isoStart);
            d.setDate(d.getDate() + ((day.dayNumber || 1) - 1));
            const dayDateStr = d.toISOString().split("T")[0];

            const [dayRes] = await conn.execute(
              `
              INSERT INTO itinerary_days (itinerary_id, day_number, date)
              VALUES (?, ?, ?)
            `,
              [itineraryId, day.dayNumber || 1, dayDateStr]
            );
            const dayId = dayRes.insertId;

            let orderIdx = 0;
            if (day.items && Array.isArray(day.items)) {
              for (const item of day.items) {
                await conn.execute(
                  `
                  INSERT INTO itinerary_items (day_id, destination_id, order_index, start_time, end_time, note)
                  VALUES (?, ?, ?, ?, ?, ?)
                `,
                  [
                    dayId,
                    item.destinationId,
                    orderIdx++,
                    item.startTime || "08:00",
                    item.endTime || "09:00",
                    item.note || ""
                  ]
                );
              }
            }
          }
        }

        await conn.commit();
        return res.json({ success: true, message: "Đã lưu lịch trình thành công!" });
      } catch (err) {
        await conn.rollback();
        throw err;
      } finally {
        conn.release();
      }
    } catch (error) {
      console.error("Save AI Itinerary Error:", error);
      const detail = error.sqlMessage || error.message;
      return res.status(500).json({ success: false, message: "Lỗi lưu DB: " + detail });
    }
  });
}
