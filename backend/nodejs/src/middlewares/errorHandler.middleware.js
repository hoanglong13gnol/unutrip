import { HttpError } from "../shared/http/HttpError.js";

/**
 * Central Express error middleware.
 *
 * Catches anything reaching `next(err)`. Built so it can be a forward-looking
 * safety net for Phase 2+ controllers without breaking the legacy handlers
 * that still build their own response.
 *
 * Behavior:
 *  - If headers were already sent, delegate so Express closes the socket.
 *  - HttpError → use its status/message; other errors → 500.
 *  - In production, hide non-HttpError messages behind "Internal server error".
 *  - Body always includes `data: null` for envelope consistency, plus
 *    `requestId` when the requestId middleware ran first and `details` when
 *    the HttpError carries them.
 *
 * Logging policy:
 *  - 5xx errors → `console.error` (full stack in dev, message-only in prod).
 *    These represent server-side bugs the operator must see.
 *  - 4xx errors → no log. They are client mistakes (bad payloads, missing
 *    auth, unknown route — including the routine `/favicon.ico` 404 from
 *    browsers). Morgan already records the request line with status, so
 *    silencing 4xx here prevents log spam without losing observability.
 *
 * @param {unknown} err
 * @param {import("express").Request} req
 * @param {import("express").Response} res
 * @param {import("express").NextFunction} next
 */
export function errorHandlerMiddleware(err, req, res, next) {
  if (res.headersSent) {
    next(err);
    return;
  }

  const isHttpError = err instanceof HttpError;
  const status = isHttpError ? err.status : 500;

  let message;
  if (isHttpError) {
    message = err.message;
  } else if (process.env.NODE_ENV === "production") {
    message = "Internal server error";
  } else {
    message = (err && err.message) || String(err);
  }

  const body = { success: false, message, data: null };
  if (isHttpError && err.details !== undefined) {
    body.details = err.details;
  }
  if (req && req.requestId) {
    body.requestId = req.requestId;
  }

  if (status >= 500) {
    if (process.env.NODE_ENV === "production") {
      console.error("[error]", {
        status,
        requestId: req && req.requestId,
        path: req && req.originalUrl,
        message: err && err.message,
      });
    } else {
      console.error("[error]", {
        status,
        requestId: req && req.requestId,
        path: req && req.originalUrl,
        message: err && err.message,
        stack: err && err.stack,
      });
    }
  }

  res.status(status).json(body);
}

export default errorHandlerMiddleware;
