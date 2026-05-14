import { describe, it, expect } from "vitest";
import { firstArrayValue, toUserDto } from "../src/shared/dto/userDto.js";

describe("userDto", () => {
  describe("firstArrayValue", () => {
    it("returns null for non-objects", () => {
      expect(firstArrayValue(null)).toBeNull();
      expect(firstArrayValue(undefined)).toBeNull();
      expect(firstArrayValue("x")).toBeNull();
    });

    it("returns first array found in object values", () => {
      expect(firstArrayValue({ a: 1, b: [2, 3] })).toEqual([2, 3]);
    });
  });

  describe("toUserDto", () => {
    it("maps user row to API DTO shape", () => {
      const row = {
        id: 1,
        full_name: "Test User",
        email: "t@example.com",
        phone: "0900",
        avatar: "/avatars/x.png",
        preferences_json: "[]",
        created_at: "2026-01-01T00:00:00.000Z"
      };
      const dto = toUserDto(row);
      expect(dto).toMatchObject({
        id: 1,
        fullName: "Test User",
        email: "t@example.com",
        phone: "0900",
        preferences: []
      });
      expect(dto.avatar).toBe("/avatars/x.png");
      expect(dto.createdAt).toBe("2026-01-01T00:00:00.000Z");
    });
  });
});
