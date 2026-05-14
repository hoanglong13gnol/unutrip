import { HttpError } from "../shared/http/HttpError.js";

/**
 * Central Express error middleware.
 *
 * Today no existing route reaches here — every legacy handler still builds its
 * own response. The middleware is a forward-looking safety net: once Phase 2+
 * handlers start calling `next(new HttpError(...))`, this is the single place
 * that turns those errors into JSON.
 *
 * Behavior is deliberately conservative:
 *  - If headers were already sent, delegate so Express closes the socket.
 *  - HttpError → use its status/message; other errors → 500.
 *  - In production, hide non-HttpError messages behind "Internal server error".
 *  - Always include `data: null` for envelope consistency, plus `requestId`
 *    when the requestId middleware ran first and `details` when the HttpError
 *    carries them.
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

  res.status(status).json(body);
}

export default errorHandlerMiddleware;
