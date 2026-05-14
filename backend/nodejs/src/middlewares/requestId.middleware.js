import { resolveRequestTrace } from "../utils.js";

/**
 * Ensures every response carries an `X-Request-ID` header and exposes the
 * resolved id (and outbound trace headers) on `req` for downstream use.
 *
 * Re-uses `utils.resolveRequestTrace` so the rules around incoming
 * `X-Request-ID` propagation stay in one place — preserving the contract
 * Node ↔ RAG already relies on.
 *
 * @param {import("express").Request} req
 * @param {import("express").Response} res
 * @param {import("express").NextFunction} next
 */
export function requestIdMiddleware(req, res, next) {
  const { requestId, traceHeaders } = resolveRequestTrace(req.headers);
  req.requestId = requestId;
  req.traceHeaders = traceHeaders;
  res.setHeader("X-Request-ID", requestId);
  next();
}

export default requestIdMiddleware;
