import { authMiddleware } from "../../auth.js";
import { upload } from "../../routes/upload.js";
import {
  getProfile,
  getStats,
  updateProfile,
  updatePreferences,
  uploadAvatar
} from "./users.controller.js";

export function registerUserRoutes(router) {
  router.get("/users/profile", authMiddleware, getProfile);
  router.get("/users/stats", authMiddleware, getStats);
  router.put("/users/profile", authMiddleware, updateProfile);
  router.put("/users/preferences", authMiddleware, updatePreferences);
  router.post("/users/avatar", authMiddleware, upload.single("avatar"), uploadAvatar);
}
