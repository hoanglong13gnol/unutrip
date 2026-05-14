import { HttpError } from "../shared/http/HttpError.js";

/**
 * Terminal middleware that converts unmatched routes into a 404 funneled
 * through `errorHandlerMiddleware`. Must be mounted after every router and
 * static mount; static handlers serve their own 404s before this runs.
 *
 * @param {import("express").Request} _req
 * @param {import("express").Response} _res
 * @param {import("express").NextFunction} next
 */
export function notFoundMiddleware(_req, _res, next) {
  next(HttpError.notFound("Route not found"));
}

export default notFoundMiddleware;
