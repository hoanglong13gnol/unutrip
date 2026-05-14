/**
 * Tests for `src/middlewares/adminAuth.middleware.js` (Phase 4 Basic
 * Auth gate). Covers the dev-mode passthrough, the one-time `console.warn`
 * guard, and the full 401 / 200 matrix in gated mode.
 *
 * Why this file uses `vi.resetModules()` + a dynamic `await import(...)`
 * instead of a static import: the middleware keeps a module-level
 * `warned` boolean that latches to `true` the first time the dev-mode
 * passthrough runs. Vitest isolates each test FILE in a worker, but
 * within a single test file, multiple `it(...)` cases share the same
 * loaded module — so without `resetModules()` the "one-time warning"
 * assertion would be order-dependent. The helper below gives every
 * test a fresh `warned = false` state by re-evaluating the middleware
 * module from scratch.
 *
 * The test builds a one-route Express app per `it(...)` so it does NOT
 * boot `createApp()`, touch the DB, or hit the RAG client.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import request from "supertest";
import express from "express";
import { Buffer } from "node:buffer";

async function loadMiddleware() {
  vi.resetModules();
  const mod = await import("../src/middlewares/adminAuth.middleware.js");
  return mod.adminAuthMiddleware;
}

function buildApp(adminAuthMiddleware) {
  const app = express();
  app.get("/admin/probe", adminAuthMiddleware, (req, res) => {
    res.type("text/plain").status(200).send("OK");
  });
  return app;
}

function basicAuthHeader(username, password) {
  const token = Buffer.from(`${username}:${password}`, "utf8").toString("base64");
  return `Basic ${token}`;
}

describe("adminAuth middleware", () => {
  let savedUser;
  let savedPass;
  let warnSpy;

  beforeEach(() => {
    savedUser = process.env.ADMIN_BASIC_USER;
    savedPass = process.env.ADMIN_BASIC_PASS;
    delete process.env.ADMIN_BASIC_USER;
    delete process.env.ADMIN_BASIC_PASS;
    warnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
  });

  afterEach(() => {
    if (savedUser === undefined) {
      delete process.env.ADMIN_BASIC_USER;
    } else {
      process.env.ADMIN_BASIC_USER = savedUser;
    }
    if (savedPass === undefined) {
      delete process.env.ADMIN_BASIC_PASS;
    } else {
      process.env.ADMIN_BASIC_PASS = savedPass;
    }
    warnSpy.mockRestore();
  });

  it("dev-mode passthrough: returns 200 OK and warns exactly once when env vars are unset", async () => {
    const mw = await loadMiddleware();
    const app = buildApp(mw);

    const res = await request(app).get("/admin/probe").expect(200);

    expect(res.text).toBe("OK");
    expect(warnSpy).toHaveBeenCalledTimes(1);
    expect(warnSpy.mock.calls[0][0]).toMatch(/ADMIN_BASIC_USER\/ADMIN_BASIC_PASS not set/);
  });

  it("dev-mode warning is one-time across multiple requests in the same module instance", async () => {
    const mw = await loadMiddleware();
    const app = buildApp(mw);

    await request(app).get("/admin/probe").expect(200);
    await request(app).get("/admin/probe").expect(200);
    await request(app).get("/admin/probe").expect(200);

    expect(warnSpy).toHaveBeenCalledTimes(1);
  });

  it("gated mode, no Authorization header → 401 Unauthorized with WWW-Authenticate", async () => {
    process.env.ADMIN_BASIC_USER = "admin";
    process.env.ADMIN_BASIC_PASS = "secret";
    const mw = await loadMiddleware();
    const app = buildApp(mw);

    const res = await request(app).get("/admin/probe").expect(401);

    expect(res.text).toBe("Unauthorized");
    expect(res.headers["www-authenticate"]).toBe('Basic realm="UnuTrip Admin"');
    expect(warnSpy).not.toHaveBeenCalled();
  });

  it("gated mode, wrong scheme (Bearer) → 401 Unauthorized", async () => {
    process.env.ADMIN_BASIC_USER = "admin";
    process.env.ADMIN_BASIC_PASS = "secret";
    const mw = await loadMiddleware();
    const app = buildApp(mw);

    const res = await request(app)
      .get("/admin/probe")
      .set("Authorization", "Bearer abc")
      .expect(401);

    expect(res.text).toBe("Unauthorized");
    expect(res.headers["www-authenticate"]).toBe('Basic realm="UnuTrip Admin"');
  });

  it("gated mode, malformed Basic value (missing colon) → 401 Unauthorized", async () => {
    process.env.ADMIN_BASIC_USER = "admin";
    process.env.ADMIN_BASIC_PASS = "secret";
    const mw = await loadMiddleware();
    const app = buildApp(mw);

    const noColon = Buffer.from("admin", "utf8").toString("base64");

    const res = await request(app)
      .get("/admin/probe")
      .set("Authorization", `Basic ${noColon}`)
      .expect(401);

    expect(res.text).toBe("Unauthorized");
    expect(res.headers["www-authenticate"]).toBe('Basic realm="UnuTrip Admin"');
  });

  it("gated mode, wrong password → 401 Unauthorized", async () => {
    process.env.ADMIN_BASIC_USER = "admin";
    process.env.ADMIN_BASIC_PASS = "secret";
    const mw = await loadMiddleware();
    const app = buildApp(mw);

    const res = await request(app)
      .get("/admin/probe")
      .set("Authorization", basicAuthHeader("admin", "wrong"))
      .expect(401);

    expect(res.text).toBe("Unauthorized");
    expect(res.headers["www-authenticate"]).toBe('Basic realm="UnuTrip Admin"');
  });

  it("gated mode, wrong username → 401 Unauthorized", async () => {
    process.env.ADMIN_BASIC_USER = "admin";
    process.env.ADMIN_BASIC_PASS = "secret";
    const mw = await loadMiddleware();
    const app = buildApp(mw);

    const res = await request(app)
      .get("/admin/probe")
      .set("Authorization", basicAuthHeader("wrong", "secret"))
      .expect(401);

    expect(res.text).toBe("Unauthorized");
    expect(res.headers["www-authenticate"]).toBe('Basic realm="UnuTrip Admin"');
  });

  it("gated mode, correct credentials → 200 OK with no WWW-Authenticate header", async () => {
    process.env.ADMIN_BASIC_USER = "admin";
    process.env.ADMIN_BASIC_PASS = "secret";
    const mw = await loadMiddleware();
    const app = buildApp(mw);

    const res = await request(app)
      .get("/admin/probe")
      .set("Authorization", basicAuthHeader("admin", "secret"))
      .expect(200);

    expect(res.text).toBe("OK");
    expect(res.headers["www-authenticate"]).toBeUndefined();
  });

  it("gated mode, password containing colons splits at the FIRST colon → 200 OK", async () => {
    process.env.ADMIN_BASIC_USER = "admin";
    process.env.ADMIN_BASIC_PASS = "s:e:c";
    const mw = await loadMiddleware();
    const app = buildApp(mw);

    const res = await request(app)
      .get("/admin/probe")
      .set("Authorization", basicAuthHeader("admin", "s:e:c"))
      .expect(200);

    expect(res.text).toBe("OK");
    expect(res.headers["www-authenticate"]).toBeUndefined();
  });
});
