import { describe, it, expect } from "vitest";
import { flattenSelectedOptionDays, itineraryRowToDto } from "../src/shared/dto/itineraryDto.js";

describe("itineraryDto", () => {
  describe("flattenSelectedOptionDays", () => {
    it("returns empty array for null/undefined", () => {
      expect(flattenSelectedOptionDays(null)).toEqual([]);
      expect(flattenSelectedOptionDays(undefined)).toEqual([]);
    });

    it("flattens items with recommendedDay from parent day", () => {
      const out = flattenSelectedOptionDays([
        { dayNumber: 2, items: [{ name: "A", rawPlaceId: "p1" }, { place_id: "p2" }] },
        { dayNumber: 3, items: [{ destinationId: 5 }] }
      ]);
      expect(out).toHaveLength(3);
      expect(out[0]).toMatchObject({ name: "A", rawPlaceId: "p1", recommendedDay: 2 });
      expect(out[1]).toMatchObject({ place_id: "p2", recommendedDay: 2 });
      expect(out[2]).toMatchObject({ destinationId: 5, recommendedDay: 3 });
    });
  });

  describe("itineraryRowToDto", () => {
    it("maps row columns to camelCase DTO", () => {
      const row = {
        id: 10,
        user_id: 2,
        title: "Hành trình",
        description: "Mô tả",
        start_date: "2026-05-01",
        end_date: "2026-05-03",
        total_days: 3,
        status: "planned",
        estimated_budget: 100,
        created_at: "2026-01-01T12:00:00.000Z"
      };
      expect(itineraryRowToDto(row, null)).toEqual({
        id: 10,
        userId: 2,
        title: "Hành trình",
        description: "Mô tả",
        startDate: "2026-05-01",
        endDate: "2026-05-03",
        totalDays: 3,
        status: "planned",
        days: null,
        estimatedBudget: 100,
        createdAt: "2026-01-01T12:00:00.000Z"
      });
    });
  });
});
