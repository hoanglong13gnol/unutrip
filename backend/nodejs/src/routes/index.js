import express from "express";
import { registerHealthRoutes } from "../modules/health/health.routes.js";
import { registerAuthRoutes } from "../modules/auth/auth.routes.js";
import { registerUserRoutes } from "../modules/users/users.routes.js";
import { registerFavoriteRoutes } from "../modules/favorites/favorites.routes.js";
import { registerDestinationRoutes } from "../modules/destinations/destinations.routes.js";
import { registerReviewRoutes } from "../modules/reviews/reviews.routes.js";
import { registerItineraryRoutes } from "../modules/itineraries/itineraries.routes.js";
import { registerAiRoutes } from "../modules/ai/ai.routes.js";

export function buildRouter() {
  const router = express.Router();
  registerHealthRoutes(router);
  registerAuthRoutes(router);
  registerUserRoutes(router);
  registerFavoriteRoutes(router);
  registerDestinationRoutes(router);
  registerReviewRoutes(router);
  registerItineraryRoutes(router);
  registerAiRoutes(router);
  return router;
}
