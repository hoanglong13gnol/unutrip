import { authMiddleware } from "../../auth.js";
import {
  listDestinations,
  listFeatured,
  listNearby,
  getDestinationDetail
} from "./destinations.controller.js";

export function registerDestinationRoutes(router) {
  router.get("/destinations", authMiddleware, listDestinations);
  router.get("/destinations/featured", authMiddleware, listFeatured);
  router.get("/destinations/nearby", authMiddleware, listNearby);
  router.get("/destinations/:id", authMiddleware, getDestinationDetail);
}
