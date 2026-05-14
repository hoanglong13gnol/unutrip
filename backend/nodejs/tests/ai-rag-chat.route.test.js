import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import request from "supertest";

vi.hoisted(() => {
  process.env.JWT_SECRET = "test-jwt-secret-for-ai-rag-chat-route-tests";
});

import { createApp } from "../src/app.js";
import { signToken } from "../src/auth.js";

describe("POST /api/ai/rag-chat", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url) => {
        if (String(url).includes("/rag/chat/simple")) {
          return new Response(
            JSON.stringify({
              answer: "Trả lời từ RAG (test)",
              places: [{ place_id: "x1", name: "Điểm A", province: "Hà Nội" }],
              warnings: [],
              latency_ms: { total: 10 },
              model_used: "mock",
              fallback_used: false,
              rag_mode: "balanced",
              runtime_mode: "mock"
            }),
            { status: 200, headers: { "Content-Type": "application/json" } }
          );
        }
        return new Response("not found", { status: 404 });
      })
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns 401 without Authorization", async () => {
    await request(createApp()).post("/api/ai/rag-chat").send({ message: "hello" }).expect(401);
  });

  it("returns 200 and normalized answer when JWT is valid", async () => {
    const token = signToken({ userId: 42, email: "user42@example.com" });
    const res = await request(createApp())
      .post("/api/ai/rag-chat")
      .set("Authorization", `Bearer ${token}`)
      .send({ message: "Gợi ý Nha Trang", top_k: 6, mode: "balanced" })
      .expect(200);

    expect(res.body.success).toBe(true);
    expect(res.body.answer).toBe("Trả lời từ RAG (test)");
    expect(Array.isArray(res.body.places)).toBe(true);
    expect(res.body.places[0].name).toBe("Điểm A");
  });
});
