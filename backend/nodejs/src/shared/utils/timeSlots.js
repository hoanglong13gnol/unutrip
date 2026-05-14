/**
 * Default `[startTime, endTime]` slots used when an AI-generated itinerary
 * item does not provide its own times. Both `createItineraryFromAiOption`
 * and `createItineraryFromAiSelection` rotate through this list.
 *
 * Order, count, and string formatting are part of the Android API contract
 * via the persisted `itinerary_items.start_time` / `end_time` columns —
 * do not modify them.
 */
export const DEFAULT_AI_ITINERARY_TIME_SLOTS = [
  ["08:00", "10:00"],
  ["10:30", "12:00"],
  ["14:00", "16:00"],
  ["16:30", "18:00"]
];
