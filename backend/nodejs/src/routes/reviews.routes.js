import { apiOk, parseJsonArray } from "../utils.js";
import { authMiddleware } from "../auth.js";
import { upload } from "./upload.js";
import { getUserById } from "./helpers.js";
import * as reviewsRepository from "../repositories/reviews.repository.js";

export function registerReviewRoutes(router) {
  router.get("/destinations/:id/reviews", authMiddleware, async (req, res) => {
    const destinationId = Number(req.params.id);
    const rows = await reviewsRepository.listReviewsByDestinationId(destinationId);

    const data = rows.map((r) => ({
      id: r.id,
      userId: r.user_id,
      userName: r.user_name,
      userAvatar: r.user_avatar,
      destinationId: r.destination_id,
      rating: r.rating,
      comment: r.comment,
      images: parseJsonArray(r.images_json, null),
      createdAt: r.created_at
    }));

    return res.json(apiOk(data, "OK"));
  });

  router.post("/reviews", authMiddleware, upload.array("images", 3), async (req, res) => {
    try {
      const destinationId = Number(req.body.destinationId);
      const rating = Number(req.body.rating);
      const comment = (req.body.comment || "").trim();

      if (!destinationId || isNaN(rating) || rating < 0 || rating > 5) {
        return res.status(400).json({ success: false, message: "Invalid payload", data: null });
      }

      const destExists = await reviewsRepository.destinationExists(destinationId);
      if (!destExists)
        return res.status(404).json({ success: false, message: "Destination not found", data: null });

      const imageUrls = (req.files || []).map((f) => `/uploads/reviews/${f.filename}`);
      const imagesJson = imageUrls.length > 0 ? JSON.stringify(imageUrls) : null;

      const info = await reviewsRepository.insertReview({
        userId: req.user.userId,
        destinationId,
        rating,
        comment,
        imagesJson
      });

      const agg = await reviewsRepository.getReviewAggregateByDestinationId(destinationId);
      await reviewsRepository.updateDestinationReviewAggregate({
        destinationId,
        rating: Number(agg.avg ?? 0),
        reviewCount: Number(agg.cnt ?? 0)
      });

      const user = await getUserById(req.user.userId);
      const review = {
        id: Number(info.lastInsertRowid),
        userId: req.user.userId,
        userName: user.full_name,
        userAvatar: user.avatar,
        destinationId,
        rating,
        comment,
        images: imageUrls.length > 0 ? imageUrls : null,
        createdAt: new Date().toISOString()
      };
      return res.json(apiOk(review, "OK"));
    } catch (err) {
      console.error("Post review error:", err);
      return res.status(500).json({ success: false, message: "Server error", data: null });
    }
  });
}
