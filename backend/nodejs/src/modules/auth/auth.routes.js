import { authMiddleware } from "../../auth.js";
import { register, login, logout } from "./auth.controller.js";

export function registerAuthRoutes(router) {
  router.post("/auth/register", register);
  router.post("/auth/login", login);
  router.post("/auth/logout", authMiddleware, logout);
}
