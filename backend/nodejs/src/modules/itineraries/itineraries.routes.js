import { authMiddleware } from "../../auth.js";
import {
  listItineraries,
  getItineraryDetail,
  createItinerary,
  addItineraryItem,
  updateItinerary,
  deleteItinerary,
  saveAiItinerary
} from "./itineraries.controller.js";

export function registerItineraryRoutes(router) {
  router.get("/itineraries", authMiddleware, listItineraries);
  router.get("/itineraries/:id", authMiddleware, getItineraryDetail);
  router.post("/itineraries", authMiddleware, createItinerary);
  router.post("/itineraries/:id/items", authMiddleware, addItineraryItem);
  router.put("/itineraries/:id", authMiddleware, updateItinerary);
  router.delete("/itineraries/:id", authMiddleware, deleteItinerary);
  router.post("/itineraries/save-ai", authMiddleware, saveAiItinerary);
}
