import crypto from "node:crypto";

/**
 * Sets `res.locals.cspNonce` for Helmet CSP `script-src` nonces on inline and
 * CDN `<script>` tags (Phase 6 admin shell + page scripts).
 */
export function cspNonceMiddleware(_req, res, next) {
  res.locals.cspNonce = crypto.randomBytes(16).toString("base64url");
  next();
}
