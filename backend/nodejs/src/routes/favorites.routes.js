import { z } from "zod";
import { apiOk } from "../utils.js";
import { authMiddleware } from "../auth.js";
import { attachDestinationImages, toDestinationDto } from "./helpers.js";
import * as favoritesRepository from "../repositories/favorites.repository.js";

export function registerFavoriteRoutes(router) {
  router.get("/users/favorites", authMiddleware, async (req, res) => {
    const rows = await favoritesRepository.listFavoriteDestinationsByUserId(req.user.userId);

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

    const destExists = await favoritesRepository.destinationExists(destinationId);
    if (!destExists)
      return res.status(404).json({ success: false, message: "Destination not found", data: null });

    await favoritesRepository.insertFavoriteIgnore(req.user.userId, destinationId);
    return res.json(apiOk(null, "OK"));
  });

  router.delete("/users/favorites/:destinationId", authMiddleware, async (req, res) => {
    const destinationId = Number(req.params.destinationId);
    await favoritesRepository.deleteFavorite(req.user.userId, destinationId);
    return res.json(apiOk(null, "OK"));
  });
}
