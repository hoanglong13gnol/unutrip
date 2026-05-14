import { authMiddleware } from "../../auth.js";
import {
  suggestItinerary,
  ragChat,
  chat,
  itineraryPreview,
  itineraryOptions,
  createFromOption,
  createFromSelection
} from "./ai.controller.js";

/**
 * NOTE: create-from-option and create-from-selection live in the ai module
 * but their public paths must remain under /api/itineraries/* (Android
 * contract). Do not move them to /api/ai/*.
 */
export function registerAiRoutes(router) {
  router.post("/ai/suggest-itinerary", authMiddleware, suggestItinerary);
  router.post("/ai/rag-chat", authMiddleware, ragChat);
  router.post("/ai/chat", authMiddleware, chat);
  router.post("/ai/itinerary-preview", authMiddleware, itineraryPreview);
  router.post("/ai/itinerary-options", authMiddleware, itineraryOptions);
  router.post("/itineraries/create-from-option", authMiddleware, createFromOption);
  router.post("/itineraries/create-from-selection", authMiddleware, createFromSelection);
}
