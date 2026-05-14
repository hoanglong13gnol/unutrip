/**
 * Locks down the admin router registration shape (Phase 4 split).
 *
 * The 18 admin endpoints are registered in a specific order by
 * `buildAdminRouter()`. A future refactor that drops a route or
 * reorders sections must trip this test rather than silently
 * regress on production.
 *
 * The factory does NOT run any SQL at boot — the section files
 * `import { db } from "../db.js"` at the top of the file, but only
 * close over `db` inside async route handlers. We still stub
 * `../src/db.js` defensively (mirrors the `tests/health.test.js`
 * pattern) so this test stays hermetic and never reaches a real
 * connection pool.
 */

import { describe, it, expect, vi } from "vitest";

vi.mock("../src/db.js", () => ({
  db: {
    pool: { query: vi.fn() },
    query: vi.fn(),
    get: vi.fn(),
    run: vi.fn()
  }
}));

import { buildAdminRouter } from "../src/admin/index.js";

function collectRoutes(router) {
  const out = [];
  for (const layer of router.stack) {
    if (!layer || !layer.route) continue;
    const path = layer.route.path;
    const methods = Object.keys(layer.route.methods || {}).filter((k) => layer.route.methods[k]);
    for (const method of methods) {
      out.push(`${method.toUpperCase()} ${path}`);
    }
  }
  return out;
}

describe("buildAdminRouter() registration shape", () => {
  it("registers exactly the 18 documented routes in order", () => {
    const router = buildAdminRouter();
    const routes = collectRoutes(router);

    const expected = [
      "GET /dashboard",
      "GET /users",
      "GET /users/api/:id",
      "POST /users/save",
      "POST /users/delete/:id",
      "GET /destinations",
      "GET /destinations/api/:id",
      "POST /destinations/save",
      "POST /destinations/delete/:id",
      "GET /system",
      "GET /rag-ai",
      "POST /rag-ai/reload-place-store",
      "POST /rag-ai/clear-cache",
      "GET /rag-ai/data-quality-issues",
      "GET /rag-ai/ai-metrics",
      "GET /rag-ai/ai-logs",
      "POST /rag-ai/debug-query",
      "GET /ai-report"
    ];

    expect(routes).toEqual(expected);
    expect(routes).toHaveLength(18);
  });
});
