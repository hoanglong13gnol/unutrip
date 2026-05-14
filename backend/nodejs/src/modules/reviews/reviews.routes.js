import { authMiddleware } from "../../auth.js";
import { upload } from "../../routes/upload.js";
import { listReviews, createReview } from "./reviews.controller.js";

export function registerReviewRoutes(router) {
  router.get("/destinations/:id/reviews", authMiddleware, listReviews);
  router.post("/reviews", authMiddleware, upload.array("images", 3), createReview);
}
