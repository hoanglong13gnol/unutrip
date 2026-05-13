import { z } from "zod";
import { apiOk } from "../utils.js";
import { authMiddleware } from "../auth.js";
import * as favoritesService from "../services/favorites.service.js";

export function registerFavoriteRoutes(router) {
  router.get("/users/favorites", authMiddleware, async (req, res) => {
    const data = await favoritesService.listUserFavorites(req.user.userId);
    return res.json({ success: true, data, total: data.length, page: 1, limit: data.length });
  });

  router.post("/users/favorites", authMiddleware, async (req, res) => {
    const schema = z.object({ destinationId: z.number().int() });
    const parsed = schema.safeParse(req.body);
    if (!parsed.success)
      return res.status(400).json({ success: false, message: "Invalid payload", data: null });
    const { destinationId } = parsed.data;

    const result = await favoritesService.addUserFavorite(req.user.userId, destinationId);
    if (!result.ok && result.reason === "destination_not_found")
      return res.status(404).json({ success: false, message: "Destination not found", data: null });

    return res.json(apiOk(null, "OK"));
  });

  router.delete("/users/favorites/:destinationId", authMiddleware, async (req, res) => {
    const destinationId = Number(req.params.destinationId);
    await favoritesService.removeUserFavorite(req.user.userId, destinationId);
    return res.json(apiOk(null, "OK"));
  });
}
