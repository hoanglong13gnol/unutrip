/**
 * HTTP Basic Auth gate for /admin/*.
 *
 * - Enabled when BOTH `ADMIN_BASIC_USER` and `ADMIN_BASIC_PASS`
 *   are present in process.env.
 * - Disabled (passthrough + one-time stderr warning) when either
 *   is missing — preserves the existing default-open behavior so
 *   running the project locally without setting the vars still
 *   works for the demo.
 *
 * The middleware does NOT call any DB or RAG service. It only
 * decodes the Authorization: Basic header and constant-time-
 * compares the credentials.
 */

import { Buffer } from "node:buffer";
import { timingSafeEqual } from "node:crypto";

let warned = false;

function warnOnce() {
  if (warned) return;
  warned = true;
  console.warn(
    "[adminAuth] ADMIN_BASIC_USER/ADMIN_BASIC_PASS not set — /admin is unauthenticated (dev mode)"
  );
}

/**
 * Constant-time compare for two UTF-8 strings.
 * Pads the shorter input with zero bytes to a common length so
 * `timingSafeEqual` (which requires equal-length buffers) is always
 * applied, then xors the length-equality back in to defeat the
 * length-leak shortcut.
 */
function constantTimeStringEquals(a, b) {
  const bufA = Buffer.from(a, "utf8");
  const bufB = Buffer.from(b, "utf8");
  const len = Math.max(bufA.length, bufB.length);
  const padA = Buffer.alloc(len);
  const padB = Buffer.alloc(len);
  bufA.copy(padA);
  bufB.copy(padB);
  const equal = timingSafeEqual(padA, padB);
  return equal && bufA.length === bufB.length;
}

function sendUnauthorized(res) {
  res.setHeader("WWW-Authenticate", 'Basic realm="UnuTrip Admin"');
  res.status(401).type("text/plain").send("Unauthorized");
}

/**
 * @param {import("express").Request} req
 * @param {import("express").Response} res
 * @param {import("express").NextFunction} next
 */
export function adminAuthMiddleware(req, res, next) {
  const user = process.env.ADMIN_BASIC_USER;
  const pass = process.env.ADMIN_BASIC_PASS;

  if (!user || !pass) {
    warnOnce();
    return next();
  }

  const header = req.headers.authorization;
  if (!header || typeof header !== "string" || !header.startsWith("Basic ")) {
    return sendUnauthorized(res);
  }

  let decoded;
  try {
    decoded = Buffer.from(header.slice(6).trim(), "base64").toString("utf8");
  } catch {
    return sendUnauthorized(res);
  }

  const sepIndex = decoded.indexOf(":");
  if (sepIndex < 0) return sendUnauthorized(res);

  const providedUser = decoded.slice(0, sepIndex);
  const providedPass = decoded.slice(sepIndex + 1);

  const userOk = constantTimeStringEquals(providedUser, user);
  const passOk = constantTimeStringEquals(providedPass, pass);
  if (!userOk || !passOk) return sendUnauthorized(res);

  return next();
}

export default adminAuthMiddleware;
