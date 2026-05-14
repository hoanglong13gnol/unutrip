import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

describe("ragPostJson retries", () => {
  beforeEach(() => {
    vi.resetModules();
    process.env.RAG_BASE_URL = "http://rag.test";
    process.env.RAG_FETCH_TIMEOUT_MS = "5000";
    process.env.RAG_FETCH_MAX_ATTEMPTS = "3";
    delete process.env.RAG_INTERNAL_API_KEY;
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("retries on 502 then succeeds", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ err: "bad" }), { status: 502 }))
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ ok: true }), {
          status: 200,
          headers: { "Content-Type": "application/json" }
        })
      );
    vi.stubGlobal("fetch", fetchMock);

    const { ragPostJson } = await import("../src/lib/ragUpstream.js");
    const out = await ragPostJson("/rag/chat/simple", { message: "hi", top_k: 3 }, {});

    expect(out.ok).toBe(true);
    expect(out.data).toEqual({ ok: true });
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
});
