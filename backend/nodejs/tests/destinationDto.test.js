import { describe, it, expect } from "vitest";
import { fixUrl, normalizeCategoryParam } from "../src/shared/dto/destinationDto.js";

describe("destinationDto", () => {
  describe("fixUrl", () => {
    it("returns empty string for falsy input", () => {
      expect(fixUrl(null)).toBe("");
      expect(fixUrl("")).toBe("");
    });

    it("keeps absolute http(s) URLs", () => {
      expect(fixUrl("https://cdn.example.com/x.png")).toBe("https://cdn.example.com/x.png");
      expect(fixUrl("http://local/img.jpg")).toBe("http://local/img.jpg");
    });

    it("prefixes bare filenames with /", () => {
      expect(fixUrl("uploads/a.jpg")).toBe("/uploads/a.jpg");
    });

    it("keeps paths that already start with /", () => {
      expect(fixUrl("/static/x.png")).toBe("/static/x.png");
    });
  });

  describe("normalizeCategoryParam", () => {
    it("returns null for empty or all-like values", () => {
      expect(normalizeCategoryParam(null)).toBeNull();
      expect(normalizeCategoryParam("")).toBeNull();
      expect(normalizeCategoryParam("all")).toBeNull();
      expect(normalizeCategoryParam("Tất Cả")).toBeNull();
    });

    it("normalizes Vietnamese synonyms", () => {
      expect(normalizeCategoryParam("bãi biển")).toBe("beach");
      expect(normalizeCategoryParam("núi")).toBe("mountain");
    });
  });
});
