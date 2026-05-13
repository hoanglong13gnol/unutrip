import { z } from "zod";
import { db } from "../db.js";
import { apiOk } from "../utils.js";
import { authMiddleware } from "../auth.js";
import { upload } from "./upload.js";
import { getUserById, toUserDto, firstArrayValue } from "./helpers.js";

export function registerUserRoutes(router) {
  router.get("/users/profile", authMiddleware, async (req, res) => {
    try {
      const user = await getUserById(req.user.userId);
      return res.json(apiOk(toUserDto(user), "OK"));
    } catch (error) {
      return res.status(404).json({ success: false, message: error.message });
    }
  });

  router.get("/users/stats", authMiddleware, async (req, res) => {
    try {
      const itineraries = await db.get("SELECT COUNT(*) as count FROM itineraries WHERE user_id = ?", [
        req.user.userId
      ]);
      const favorites = await db.get("SELECT COUNT(*) as count FROM favorites WHERE user_id = ?", [
        req.user.userId
      ]);
      const reviews = await db.get("SELECT COUNT(*) as count FROM reviews WHERE user_id = ?", [
        req.user.userId
      ]);

      return res.json(
        apiOk(
          {
            itineraryCount: itineraries.count,
            favoriteCount: favorites.count,
            reviewCount: reviews.count
          },
          "OK"
        )
      );
    } catch (error) {
      return res.status(500).json({ success: false, message: error.message });
    }
  });

  router.put("/users/profile", authMiddleware, async (req, res) => {
    const schema = z.object({
      id: z.number().int().optional(),
      fullName: z.string().min(1),
      email: z.string().email(),
      phone: z.string().optional().nullable(),
      avatar: z.string().optional().nullable(),
      preferences: z.array(z.string()).optional().nullable()
    });
    const parsed = schema.safeParse(req.body);
    if (!parsed.success) return res.status(400).json({ success: false, message: "Invalid payload" });

    const { fullName, email, phone, avatar, preferences } = parsed.data;
    const existing = await db.get("SELECT id FROM users WHERE email = ? AND id != ?", [
      email,
      req.user.userId
    ]);
    if (existing) return res.status(400).json({ success: false, message: "Email đã được dùng" });

    await db.run(
      "UPDATE users SET full_name = ?, email = ?, phone = ?, avatar = ?, preferences_json = COALESCE(?, preferences_json) WHERE id = ?",
      [
        fullName,
        email,
        phone ?? null,
        avatar ?? null,
        preferences ? JSON.stringify(preferences) : null,
        req.user.userId
      ]
    );

    const user = await getUserById(req.user.userId);
    return res.json(apiOk(toUserDto(user), "Cập nhật thành công"));
  });

  router.put("/users/preferences", authMiddleware, async (req, res) => {
    const body = req.body ?? {};
    const prefs = Array.isArray(body.preferences)
      ? body.preferences
      : Array.isArray(body.preference)
        ? body.preference
        : firstArrayValue(body);

    if (!Array.isArray(prefs)) return res.status(400).json({ success: false, message: "Invalid payload" });
    await db.run("UPDATE users SET preferences_json = ? WHERE id = ?", [
      JSON.stringify(prefs),
      req.user.userId
    ]);
    const user = await getUserById(req.user.userId);
    return res.json(apiOk(toUserDto(user), "OK"));
  });

  router.post("/users/avatar", authMiddleware, upload.single("avatar"), async (req, res) => {
    if (!req.file) return res.status(400).json({ success: false, message: "No file uploaded" });
    const avatarUrl = `/uploads/avatars/${req.file.filename}`;
    await db.run("UPDATE users SET avatar = ? WHERE id = ?", [avatarUrl, req.user.userId]);
    const user = await getUserById(req.user.userId);
    return res.json(apiOk(toUserDto(user), "Cập nhật ảnh đại diện thành công"));
  });
}
