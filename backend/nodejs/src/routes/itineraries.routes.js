import { z } from "zod";
import { db } from "../db.js";
import { apiOk, daysBetweenInclusive, toIsoDate } from "../utils.js";
import { authMiddleware } from "../auth.js";
import * as itinerariesRepository from "../repositories/itineraries.repository.js";
import {
  itineraryRowToDto,
  toDestinationDto
} from "./helpers.js";

export function registerItineraryRoutes(router) {
  router.get("/itineraries", authMiddleware, async (req, res) => {
    const rows = await itinerariesRepository.listItinerariesByUserId(req.user.userId);

    const data = rows.map((r) => itineraryRowToDto(r, null));
    return res.json({ success: true, data });
  });

  router.get("/itineraries/:id", authMiddleware, async (req, res) => {
    const id = Number(req.params.id);
    const it = await itinerariesRepository.getItineraryByIdForUser({ itineraryId: id, userId: req.user.userId });
    if (!it) return res.status(404).json({ success: false, message: "Not found", data: null });

    const days = await itinerariesRepository.listItineraryDaysByItineraryId(id);
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

    const info = await itinerariesRepository.insertItinerary({
      userId: req.user.userId,
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
    return res.json(apiOk(itineraryRowToDto(it, null), "OK"));
  });

  router.post("/itineraries/:id/items", authMiddleware, async (req, res) => {
    try {
      const itineraryId = Number(req.params.id);
      const { destinationId, dayId, startTime, endTime, note } = req.body;

      if (!destinationId) {
        return res.status(400).json({ success: false, message: "Missing destinationId" });
      }

      const it = await itinerariesRepository.getItineraryByIdForUser({
        itineraryId,
        userId: req.user.userId
      });
      if (!it) return res.status(403).json({ success: false, message: "Not authorized or not found" });

      let targetDayId = dayId;
      if (!targetDayId) {
        const firstDayId = await itinerariesRepository.getFirstItineraryDayId(itineraryId);
        if (!firstDayId) return res.status(400).json({ success: false, message: "No days in itinerary" });
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

      return res.json({ success: true, message: "Đã thêm vào lịch trình" });
    } catch (e) {
      console.error(e);
      return res.status(500).json({ success: false, message: "Server Error" });
    }
  });

  router.put("/itineraries/:id", authMiddleware, async (req, res) => {
    const id = Number(req.params.id);
    const it = await itinerariesRepository.getItineraryByIdForUser({ itineraryId: id, userId: req.user.userId });
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
    await itinerariesRepository.updateItineraryByIdForUser({
      itineraryId: id,
      userId: req.user.userId,
      title: parsed.data.title,
      description: parsed.data.description,
      startDate: toIsoDate(parsed.data.startDate),
      endDate: toIsoDate(parsed.data.endDate),
      totalDays,
      status: parsed.data.status,
      estimatedBudget: parsed.data.estimatedBudget ?? null
    });

    const updated = await itinerariesRepository.getItineraryById(id);
    return res.json(apiOk(itineraryRowToDto(updated, null), "OK"));
  });

  router.delete("/itineraries/:id", authMiddleware, async (req, res) => {
    const id = Number(req.params.id);
    await itinerariesRepository.deleteItineraryByIdForUser({ itineraryId: id, userId: req.user.userId });
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

        const itinRes = await itinerariesRepository.insertItinerary(
          {
            userId: req.user.userId,
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
