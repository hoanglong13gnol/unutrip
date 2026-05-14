import { apiOk } from "../../utils.js";
import * as reviewsService from "../../services/reviews.service.js";

export async function listReviews(req, res) {
  const destinationId = Number(req.params.id);
  const data = await reviewsService.listReviewsForDestination(destinationId);
  return res.json(apiOk(data, "OK"));
}

export async function createReview(req, res) {
  try {
    const destinationId = Number(req.body.destinationId);
    const rating = Number(req.body.rating);
    const comment = (req.body.comment || "").trim();

    if (!destinationId || isNaN(rating) || rating < 0 || rating > 5) {
      return res.status(400).json({ success: false, message: "Invalid payload", data: null });
    }

    const imageUrls = (req.files || []).map((f) => `/uploads/reviews/${f.filename}`);

    const result = await reviewsService.createReview({
      userId: req.user.userId,
      destinationId,
      rating,
      comment,
      imageUrls
    });

    if (!result.ok && result.reason === "destination_not_found") {
      return res.status(404).json({ success: false, message: "Destination not found", data: null });
    }

    return res.json(apiOk(result.review, "OK"));
  } catch (err) {
    console.error("Post review error:", err);
    return res.status(500).json({ success: false, message: "Server error", data: null });
  }
}
