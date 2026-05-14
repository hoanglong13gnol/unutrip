/**
 * Wraps an async Express handler so any rejection is forwarded to `next(err)`
 * instead of becoming an unhandled promise rejection.
 *
 * @template {Function} F
 * @param {F} fn Async (or sync) Express handler `(req, res, next) => any`.
 * @returns {(req: import("express").Request, res: import("express").Response, next: import("express").NextFunction) => void}
 */
export function asyncHandler(fn) {
  return function asyncHandlerWrapper(req, res, next) {
    Promise.resolve(fn(req, res, next)).catch(next);
  };
}

export default asyncHandler;
