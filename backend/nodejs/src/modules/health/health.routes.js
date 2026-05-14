import { getHealth, getHealthReady } from "./health.controller.js";

/**
 * Liveness + readiness for orchestrators (Docker / k8s).
 * @param {import("express").Router} router
 */
export function registerHealthRoutes(router) {
  router.get("/health", getHealth);
  router.get("/health/ready", getHealthReady);
}
