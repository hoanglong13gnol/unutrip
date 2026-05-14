import { z } from "zod";
import { apiOk, daysBetweenInclusive, toIsoDate } from "../../utils.js";
import * as itinerariesService from "../../services/itineraries.service.js";

export async function listItineraries(req, res) {
  const data = await itinerariesService.listItinerariesForUser(req.user.userId);
  return res.json({ success: true, data });
}

export async function getItineraryDetail(req, res) {
  const id = Number(req.params.id);
  const result = await itinerariesService.getItineraryDetailForUser({
    userId: req.user.userId,
    itineraryId: id
  });
  if (!result.ok) return res.status(404).json({ success: false, message: "Not found", data: null });
  return res.json(apiOk(result.data, "OK"));
}

export async function createItinerary(req, res) {
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
}

export async function addItineraryItem(req, res) {
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
    if (!result.ok && result.reason === "invalid_day") {
      return res.status(400).json({ success: false, message: "Ngày không thuộc lịch trình này" });
    }

    return res.json({ success: true, message: "Đã thêm vào lịch trình" });
  } catch (e) {
    console.error(e);
    return res.status(500).json({ success: false, message: "Server Error" });
  }
}

export async function updateItinerary(req, res) {
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
}

export async function updateItineraryItem(req, res) {
  const itineraryId = Number(req.params.id);
  const itemId = Number(req.params.itemId);

  const schema = z.object({
    dayId: z.number().int().optional(),
    destinationId: z.number().int().optional(),
    startTime: z.string().min(1).optional(),
    endTime: z.string().min(1).optional(),
    note: z.string().optional().nullable(),
    orderIndex: z.number().int().optional()
  });
  const parsed = schema.safeParse(req.body);
  if (!parsed.success) {
    return res.status(400).json({ success: false, message: "Invalid payload", data: null });
  }

  const result = await itinerariesService.updateItineraryItemForUser({
    userId: req.user.userId,
    itineraryId,
    itemId,
    payload: parsed.data
  });

  if (!result.ok && result.reason === "not_authorized") {
    return res.status(403).json({ success: false, message: "Not authorized or not found" });
  }
  if (!result.ok && result.reason === "not_found") {
    return res.status(404).json({ success: false, message: "Not found" });
  }
  if (!result.ok && result.reason === "invalid_day") {
    return res.status(400).json({ success: false, message: "Ngày không hợp lệ" });
  }
  if (!result.ok && result.reason === "missing_destination_id") {
    return res.status(400).json({ success: false, message: "Missing destinationId" });
  }

  return res.json(apiOk(null, "Đã cập nhật hoạt động"));
}

export async function addItineraryDay(req, res) {
  const itineraryId = Number(req.params.id);
  const result = await itinerariesService.addItineraryDayForUser({
    userId: req.user.userId,
    itineraryId
  });

  if (!result.ok && result.reason === "not_authorized") {
    return res.status(403).json({ success: false, message: "Not authorized or not found" });
  }

  return res.json(apiOk(null, "Đã thêm ngày"));
}

export async function deleteItineraryDay(req, res) {
  const itineraryId = Number(req.params.id);
  const dayId = Number(req.params.dayId);

  const result = await itinerariesService.deleteItineraryDayForUser({
    userId: req.user.userId,
    itineraryId,
    dayId
  });

  if (!result.ok && result.reason === "not_authorized") {
    return res.status(403).json({ success: false, message: "Not authorized or not found" });
  }
  if (!result.ok && result.reason === "not_found") {
    return res.status(404).json({ success: false, message: "Not found" });
  }
  if (!result.ok && result.reason === "last_day") {
    return res.status(400).json({
      success: false,
      message: "Cần ít nhất một ngày trong lịch trình"
    });
  }

  return res.json(apiOk(null, "Đã xóa ngày"));
}

export async function deleteItineraryItem(req, res) {
  const itineraryId = Number(req.params.id);
  const itemId = Number(req.params.itemId);

  const result = await itinerariesService.deleteItineraryItemForUser({
    userId: req.user.userId,
    itineraryId,
    itemId
  });

  if (!result.ok && result.reason === "not_authorized") {
    return res.status(403).json({ success: false, message: "Not authorized or not found" });
  }
  if (!result.ok && result.reason === "not_found") {
    return res.status(404).json({ success: false, message: "Not found" });
  }

  return res.json(apiOk(null, "Đã xóa hoạt động"));
}

export async function deleteItinerary(req, res) {
  const id = Number(req.params.id);
  await itinerariesService.deleteItineraryForUser({ userId: req.user.userId, itineraryId: id });
  return res.json(apiOk(null, "OK"));
}

export async function saveAiItinerary(req, res) {
  try {
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
}
