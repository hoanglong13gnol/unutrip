import { describe, it, expect } from "vitest";
import { normalizeRagChatSimpleResponse } from "../src/schemas/ragContract.js";

describe("normalizeRagChatSimpleResponse", () => {
  it("accepts a valid FastAPI-shaped payload", () => {
    const out = normalizeRagChatSimpleResponse({
      answer: "Chào bạn",
      places: [{ place_id: "p1", name: "Biển", province: "Khánh Hòa" }],
      warnings: ["cảnh báo"],
      latency_ms: { total: 42 },
      model_used: "gemini-2.5-flash",
      fallback_used: false,
      rag_mode: "balanced",
      runtime_mode: "demo"
    });
    expect(out.ok).toBe(true);
    expect(out.issues).toHaveLength(0);
    expect(out.data.answer).toBe("Chào bạn");
    expect(out.data.places).toHaveLength(1);
  });

  it("coerces invalid payloads with issues logged path", () => {
    const out = normalizeRagChatSimpleResponse({
      answer: 123,
      places: "nope",
      warnings: [1, 2]
    });
    expect(out.ok).toBe(false);
    expect(out.issues.length).toBeGreaterThan(0);
    expect(out.data.answer).toBe("");
    expect(out.data.places).toEqual([]);
  });
});
