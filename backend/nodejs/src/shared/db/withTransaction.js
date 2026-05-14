import { db } from "../../db.js";

/**
 * Run `work(conn)` inside a single MySQL transaction.
 *
 * BEGIN / COMMIT / ROLLBACK and connection release are handled here so callers
 * can focus on the business logic. The connection is taken from the shared
 * pool exposed by `src/db.js` via `db.pool` — this helper does NOT modify
 * `db.js`.
 *
 * Intended for Phase 3 itinerary/AI flows; no existing service uses it yet.
 *
 * @template T
 * @param {(conn: import("mysql2/promise").PoolConnection) => Promise<T>} work
 * @returns {Promise<T>}
 */
export async function withTransaction(work) {
  const conn = await db.pool.getConnection();
  try {
    await conn.beginTransaction();
    const result = await work(conn);
    await conn.commit();
    return result;
  } catch (err) {
    try {
      await conn.rollback();
    } catch {
      // ignored: a failed rollback (e.g. lost connection) must not mask the original error
    }
    throw err;
  } finally {
    conn.release();
  }
}

export default withTransaction;
