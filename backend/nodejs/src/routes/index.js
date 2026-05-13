import express from "express";
import { registerAuthRoutes } from "./auth.routes.js";
import { registerUserRoutes } from "./users.routes.js";
import { registerFavoriteRoutes } from "./favorites.routes.js";
import { registerDestinationRoutes } from "./destinations.routes.js";
import { registerReviewRoutes } from "./reviews.routes.js";
import { registerItineraryRoutes } from "./itineraries.routes.js";
import { registerAiRoutes } from "./ai.routes.js";

export function buildRouter() {
  const router = express.Router();
  registerAuthRoutes(router);
  registerUserRoutes(router);
  registerFavoriteRoutes(router);
  registerDestinationRoutes(router);
  registerReviewRoutes(router);
  registerItineraryRoutes(router);
  registerAiRoutes(router);
  return router;
}
