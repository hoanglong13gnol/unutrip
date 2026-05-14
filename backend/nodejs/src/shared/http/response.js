/**
 * Canonical success / failure envelope helpers.
 *
 * `apiOk` and `apiFail` are kept BIT-IDENTICAL to the previous `src/utils.js`
 * implementations so existing routes/services that import them via
 * `../utils.js` continue to produce the exact same response objects.
 *
 * `apiList` is a new helper for future list endpoints. It is intentionally
 * NOT wired into any existing route in Phase 1 — it just sits ready.
 */

/**
 * @template T
 * @param {T} data
 * @param {string} [message="OK"]
 * @returns {{ success: true, message: string, data: T }}
 */
export function apiOk(data, message = "OK") {
  return { success: true, message, data };
}

/**
 * @param {string} [message="Error"]
 * @param {number} [status=400]
 * @param {unknown} [data=null]
 * @returns {{ status: number, body: { success: false, message: string, data: unknown } }}
 */
export function apiFail(message = "Error", status = 400, data = null) {
  return { status, body: { success: false, message, data } };
}

/**
 * Future-use list envelope. Not used by any existing handler yet.
 *
 * @template T
 * @param {{ data: T[], total: number, page?: number, limit?: number }} params
 * @returns {{ success: true, data: T[], total: number, page: number, limit: number }}
 */
export function apiList({ data, total, page = 1, limit = Array.isArray(data) ? data.length : 0 }) {
  return { success: true, data, total, page, limit };
}
