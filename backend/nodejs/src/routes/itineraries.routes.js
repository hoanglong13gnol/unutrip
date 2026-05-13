import { z } from "zod";
import { apiOk, daysBetweenInclusive, toIsoDate } from "../utils.js";
import { authMiddleware } from "../auth.js";
import * as itinerariesService from "../services/itineraries.service.js";

export function registerItineraryRoutes(router) {
  router.get("/itineraries", authMiddleware, async (req, res) => {
    const data = await itinerariesService.listItinerariesForUser(req.user.userId);
    return res.json({ success: true, data });
  });

  router.get("/itineraries/:id", authMiddleware, async (req, res) => {
    const id = Number(req.params.id);
    const result = await itinerariesService.getItineraryDetailForUser({
      userId: req.user.userId,
      itineraryId: id
    });
    if (!result.ok) return res.status(404).json({ success: false, message: "Not found", data: null });
    return res.json(apiOk(result.data, "OK"));
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

    const dto = await itinerariesService.createItineraryWithDaysAndItems({
      userId: req.user.userId,
      payload: {
        title,
        description,
        startDate,
        endDate,
        destinationIds,
        estimatedBudget,
        totalDays
      }
    });
    return res.json(apiOk(dto, "OK"));
  });

  router.post("/itineraries/:id/items", authMiddleware, async (req, res) => {
    try {
      const itineraryId = Number(req.params.id);
      const { destinationId, dayId, startTime, endTime, note } = req.body;

      const result = await itinerariesService.addItineraryItem({
        userId: req.user.userId,
        itineraryId,
        payload: { destinationId, dayId, startTime, endTime, note }
      });

      if (!result.ok && result.reason === "missing_destination_id") {
        return res.status(400).json({ success: false, message: "Missing destinationId" });
      }
      if (!result.ok && result.reason === "not_authorized") {
        return res.status(403).json({ success: false, message: "Not authorized or not found" });
      }
      if (!result.ok && result.reason === "no_days") {
        return res.status(400).json({ success: false, message: "No days in itinerary" });
      }

      return res.json({ success: true, message: "Đã thêm vào lịch trình" });
    } catch (e) {
      console.error(e);
      return res.status(500).json({ success: false, message: "Server Error" });
    }
  });

  router.put("/itineraries/:id", authMiddleware, async (req, res) => {
    const id = Number(req.params.id);
    const it = await itinerariesService.getItineraryForUser({ userId: req.user.userId, itineraryId: id });
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
    const updatedDto = await itinerariesService.updateItineraryForUser({
      userId: req.user.userId,
      itineraryId: id,
      payload: {
        title: parsed.data.title,
        description: parsed.data.description,
        startDate: toIsoDate(parsed.data.startDate),
        endDate: toIsoDate(parsed.data.endDate),
        totalDays,
        status: parsed.data.status,
        estimatedBudget: parsed.data.estimatedBudget ?? null
      }
    });

    return res.json(apiOk(updatedDto, "OK"));
  });

  router.delete("/itineraries/:id", authMiddleware, async (req, res) => {
    const id = Number(req.params.id);
    await itinerariesService.deleteItineraryForUser({ userId: req.user.userId, itineraryId: id });
    return res.json(apiOk(null, "OK"));
  });

  router.post("/itineraries/save-ai", authMiddleware, async (req, res) => {
    try {
      console.log("[AI] Save AI Itinerary Request:", JSON.stringify(req.body).substring(0, 500));
      const { title, description, startDate, endDate, budget, days } = req.body;

      await itinerariesService.saveAiItinerary({
        userId: req.user.userId,
        payload: { title, description, startDate, endDate, budget, days }
      });

      return res.json({ success: true, message: "Đã lưu lịch trình thành công!" });
    } catch (error) {
      console.error("Save AI Itinerary Error:", error);
      const detail = error.sqlMessage || error.message;
      return res.status(500).json({ success: false, message: "Lỗi lưu DB: " + detail });
    }
  });
}
