import { z } from "zod";
import { db } from "../db.js";
import { apiOk } from "../utils.js";
import { authMiddleware } from "../auth.js";
import { attachDestinationImages, toDestinationDto } from "./helpers.js";

export function registerFavoriteRoutes(router) {
  router.get("/users/favorites", authMiddleware, async (req, res) => {
    const rows = await db.query(
      `
      SELECT d.*, 1 as is_favorite
      FROM favorites f
      JOIN destinations d ON d.id = f.destination_id
      WHERE f.user_id = ?
      ORDER BY f.created_at DESC
    `,
      [req.user.userId]
    );

    const rowsWithImages = await attachDestinationImages(rows);
    const data = rowsWithImages.map((r) => toDestinationDto(r, true));
    return res.json({ success: true, data, total: data.length, page: 1, limit: data.length });
  });

  router.post("/users/favorites", authMiddleware, async (req, res) => {
    const schema = z.object({ destinationId: z.number().int() });
    const parsed = schema.safeParse(req.body);
    if (!parsed.success)
      return res.status(400).json({ success: false, message: "Invalid payload", data: null });
    const { destinationId } = parsed.data;

    const dest = await db.get("SELECT id FROM destinations WHERE id = ?", [destinationId]);
    if (!dest) return res.status(404).json({ success: false, message: "Destination not found", data: null });

    await db.run("INSERT IGNORE INTO favorites (user_id, destination_id) VALUES (?, ?)", [
      req.user.userId,
      destinationId
    ]);
    return res.json(apiOk(null, "OK"));
  });

  router.delete("/users/favorites/:destinationId", authMiddleware, async (req, res) => {
    const destinationId = Number(req.params.destinationId);
    await db.run("DELETE FROM favorites WHERE user_id = ? AND destination_id = ?", [
      req.user.userId,
      destinationId
    ]);
    return res.json(apiOk(null, "OK"));
  });
}
