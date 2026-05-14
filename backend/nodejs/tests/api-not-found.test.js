import { describe, it, expect } from "vitest";
import request from "supertest";
import { createApp } from "../src/app.js";

describe("Unmatched API paths", () => {
  it("GET unknown /api route returns 404 JSON envelope", async () => {
    const res = await request(createApp())
      .get("/api/__vitest_no_such_route__")
      .expect(404);

    expect(res.body.success).toBe(false);
    expect(res.body.message).toBe("Route not found");
    expect(res.body.data).toBeNull();
  });
});
