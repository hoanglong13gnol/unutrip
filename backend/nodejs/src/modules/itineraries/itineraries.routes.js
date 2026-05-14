import { authMiddleware } from "../../auth.js";
import {
  listItineraries,
  getItineraryDetail,
  createItinerary,
  addItineraryItem,
  updateItineraryItem,
  deleteItineraryItem,
  updateItinerary,
  deleteItinerary,
  saveAiItinerary,
  addItineraryDay,
  deleteItineraryDay
} from "./itineraries.controller.js";

export function registerItineraryRoutes(router) {
  router.get("/itineraries", authMiddleware, listItineraries);
  router.get("/itineraries/:id", authMiddleware, getItineraryDetail);
  router.post("/itineraries", authMiddleware, createItinerary);
  router.post("/itineraries/:id/days", authMiddleware, addItineraryDay);
  router.delete("/itineraries/:id/days/:dayId", authMiddleware, deleteItineraryDay);
  router.post("/itineraries/:id/items", authMiddleware, addItineraryItem);
  router.put("/itineraries/:id/items/:itemId", authMiddleware, updateItineraryItem);
  router.delete("/itineraries/:id/items/:itemId", authMiddleware, deleteItineraryItem);
  router.put("/itineraries/:id", authMiddleware, updateItinerary);
  router.delete("/itineraries/:id", authMiddleware, deleteItinerary);
  router.post("/itineraries/save-ai", authMiddleware, saveAiItinerary);
}
