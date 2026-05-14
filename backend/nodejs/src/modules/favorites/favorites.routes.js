import { authMiddleware } from "../../auth.js";
import { listFavorites, addFavorite, removeFavorite } from "./favorites.controller.js";

export function registerFavoriteRoutes(router) {
  router.get("/users/favorites", authMiddleware, listFavorites);
  router.post("/users/favorites", authMiddleware, addFavorite);
  router.delete("/users/favorites/:destinationId", authMiddleware, removeFavorite);
}
