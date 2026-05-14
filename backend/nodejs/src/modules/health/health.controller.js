import { db } from "../../db.js";
import { ragUrl, ragAuthHeaders } from "../../config/ragClient.js";
import { HEALTHCHECK_SKIP_RAG } from "../../config/env.js";

export function getHealth(req, res) {
  res.json({
    ok: true,
    service: "smarttravel-backend",
    uptime_s: Math.round(process.uptime()),
  });
}

export async function getHealthReady(req, res) {
  /** @type {{ database: boolean, rag?: boolean | null, error?: string }} */
  const checks = { database: false, rag: null };

  try {
    await db.pool.query("SELECT 1 AS ok");
    checks.database = true;
  } catch (err) {
    checks.error = /** @type {Error} */ (err).message;
    return res.status(503).json({ ok: false, checks });
  }

  if (HEALTHCHECK_SKIP_RAG) {
    checks.rag = null;
    return res.json({ ok: true, checks });
  }

  try {
    const ragHealthUrl = ragUrl("/health");
    const ragRes = await fetch(ragHealthUrl, {
      method: "GET",
      headers: ragAuthHeaders(),
      signal: AbortSignal.timeout(5000),
    });
    checks.rag = ragRes.ok;
    if (!ragRes.ok) {
      return res.status(503).json({ ok: false, checks });
    }
  } catch (err) {
    checks.rag = false;
    checks.error = /** @type {Error} */ (err).message;
    return res.status(503).json({ ok: false, checks });
  }

  return res.json({ ok: true, checks });
}
