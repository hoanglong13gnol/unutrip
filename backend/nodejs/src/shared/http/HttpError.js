/**
 * Typed HTTP error usable by route handlers and the central error middleware.
 *
 * Handlers can `throw new HttpError(404, "Not found")` (or use the named static
 * factories) and the central `errorHandlerMiddleware` will translate it into
 * a JSON response with the matching status code.
 *
 * Pure class with no dependency on any project module so it stays safe to
 * import from anywhere (including future tests and tooling).
 */
export class HttpError extends Error {
  /**
   * @param {number} status HTTP status code (e.g. 400, 404, 500).
   * @param {string} message Human-readable message.
   * @param {{ code?: string, details?: unknown, expose?: boolean, cause?: unknown }} [options]
   */
  constructor(status, message, options = {}) {
    super(message);
    this.name = "HttpError";
    this.status = Number(status) || 500;
    this.message = message;
    if (options && typeof options.code === "string") {
      this.code = options.code;
    }
    if (options && options.details !== undefined) {
      this.details = options.details;
    }
    this.expose =
      options && typeof options.expose === "boolean" ? options.expose : this.status < 500;
    if (options && options.cause !== undefined) {
      this.cause = options.cause;
    }
    if (typeof Error.captureStackTrace === "function") {
      Error.captureStackTrace(this, HttpError);
    }
  }

  static badRequest(message = "Bad request", details) {
    return new HttpError(400, message, details === undefined ? undefined : { details });
  }

  static unauthorized(message = "Unauthorized") {
    return new HttpError(401, message);
  }

  static forbidden(message = "Forbidden") {
    return new HttpError(403, message);
  }

  static notFound(message = "Not found") {
    return new HttpError(404, message);
  }

  static conflict(message = "Conflict") {
    return new HttpError(409, message);
  }

  static upstream(message = "Upstream error", details) {
    return new HttpError(502, message, details === undefined ? undefined : { details });
  }

  static internal(message = "Internal server error", details) {
    return new HttpError(500, message, details === undefined ? undefined : { details });
  }
}
