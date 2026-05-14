import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import request from "supertest";

const queryMock = vi.fn();

vi.mock("../src/db.js", () => ({
  db: {
    pool: {
      query: (...args) => queryMock(...args)
    }
  }
}));

import { createApp } from "../src/app.js";

describe("HTTP health", () => {
  beforeEach(() => {
    queryMock.mockResolvedValue([[{ ok: 1 }]]);
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url) => {
        const u = String(url);
        if (u.includes("/health") && !u.includes("/health/ready")) {
          return new Response(JSON.stringify({ status: "ok" }), {
            status: 200,
            headers: { "Content-Type": "application/json" }
          });
        }
        return new Response("not found", { status: 404 });
      })
    );
  });

  afterEach(() => {
    vi.clearAllMocks();
    vi.unstubAllGlobals();
  });

  it("GET /api/health returns liveness", async () => {
    const res = await request(createApp()).get("/api/health").expect(200);
    expect(res.body.ok).toBe(true);
    expect(res.body.service).toBe("smarttravel-backend");
  });

  it("GET /api/health/ready returns 200 when DB and RAG health succeed", async () => {
    const res = await request(createApp()).get("/api/health/ready").expect(200);
    expect(res.body.ok).toBe(true);
    expect(res.body.checks.database).toBe(true);
    expect(res.body.checks.rag).toBe(true);
  });
});
