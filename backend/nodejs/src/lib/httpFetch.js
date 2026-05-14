/**
 * Small fetch helpers: bounded wait time and merged abort signals.
 */

/**
 * @param {string|URL} url
 * @param {RequestInit} [init]
 * @param {number} timeoutMs
 * @returns {Promise<Response>}
 */
export async function fetchWithTimeout(url, init = {}, timeoutMs) {
  const outer = init.signal;
  const timer = AbortSignal.timeout(Math.max(1, timeoutMs));
  const signal = outer ? AbortSignal.any([outer, timer]) : timer;
  return fetch(url, { ...init, signal });
}
