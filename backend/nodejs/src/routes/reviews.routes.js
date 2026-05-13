import { db } from "../db.js";
import { apiOk, parseJsonArray } from "../utils.js";
import { authMiddleware } from "../auth.js";
import { upload } from "./upload.js";
import { getUserById } from "./helpers.js";

export function registerReviewRoutes(router) {
  router.get("/destinations/:id/reviews", authMiddleware, async (req, res) => {
    const destinationId = Number(req.params.id);
    const rows = await db.query(
      `
      SELECT r.id, r.user_id, u.full_name as user_name, u.avatar as user_avatar,
             r.destination_id, r.rating, r.comment, r.images_json, r.created_at
      FROM reviews r
      JOIN users u ON u.id = r.user_id
      WHERE r.destination_id = ?
      ORDER BY r.created_at DESC, r.id DESC
    `,
      [destinationId]
    );

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

      const dest = await db.get("SELECT id FROM destinations WHERE id = ?", [destinationId]);
      if (!dest) return res.status(404).json({ success: false, message: "Destination not found", data: null });

      const imageUrls = (req.files || []).map((f) => `/uploads/reviews/${f.filename}`);
      const imagesJson = imageUrls.length > 0 ? JSON.stringify(imageUrls) : null;

      const info = await db.run(
        "INSERT INTO reviews (user_id, destination_id, rating, comment, images_json) VALUES (?, ?, ?, ?, ?)",
        [req.user.userId, destinationId, rating, comment, imagesJson]
      );

      const agg = await db.get("SELECT AVG(rating) as avg, COUNT(*) as cnt FROM reviews WHERE destination_id = ?", [
        destinationId
      ]);
      await db.run("UPDATE destinations SET rating = ?, review_count = ? WHERE id = ?", [
        Number(agg.avg ?? 0),
        Number(agg.cnt ?? 0),
        destinationId
      ]);

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
