import bcrypt from "bcryptjs";
import { z } from "zod";
import { db } from "../db.js";
import { apiOk } from "../utils.js";
import { authMiddleware, signToken } from "../auth.js";
import { toUserDto } from "./helpers.js";

export function registerAuthRoutes(router) {
  router.get("/health", (req, res) => res.json({ ok: true, name: "smarttravel-backend" }));

  router.post("/auth/register", async (req, res) => {
    const schema = z.object({
      fullName: z.string().min(1),
      email: z.string().email(),
      password: z.string().min(4),
      phone: z.string().optional().nullable()
    });

    const parsed = schema.safeParse(req.body);
    if (!parsed.success) return res.status(400).json({ success: false, message: "Invalid payload" });
    const { fullName, email, password, phone } = parsed.data;

    const exists = await db.get("SELECT id FROM users WHERE email = ?", [email]);
    if (exists) return res.status(400).json({ success: false, message: "Email đã tồn tại" });

    const passwordHash = bcrypt.hashSync(password, 10);
    const info = await db.run(
      "INSERT INTO users (full_name, email, password_hash, phone, avatar, preferences_json) VALUES (?, ?, ?, ?, ?, ?)",
      [fullName, email, passwordHash, phone ?? null, null, JSON.stringify([])]
    );

    const user = await db.get(
      "SELECT id, full_name, email, phone, avatar, preferences_json, created_at FROM users WHERE id = ?",
      [info.lastInsertRowid]
    );

    const token = signToken({ userId: user.id, email: user.email });

    return res.json({
      success: true,
      message: "Đăng ký thành công",
      token,
      user: toUserDto(user)
    });
  });

  router.post("/auth/login", async (req, res) => {
    const schema = z.object({
      email: z.string().email(),
      password: z.string().min(1)
    });

    const parsed = schema.safeParse(req.body);
    if (!parsed.success) return res.status(400).json({ success: false, message: "Invalid payload" });
    const { email, password } = parsed.data;

    const user = await db.get(
      "SELECT id, full_name, email, password_hash, phone, avatar, preferences_json, created_at FROM users WHERE email = ?",
      [email]
    );
    if (!user) return res.status(401).json({ success: false, message: "Sai email hoặc mật khẩu" });

    const ok = bcrypt.compareSync(password, user.password_hash);
    if (!ok) return res.status(401).json({ success: false, message: "Sai email hoặc mật khẩu" });

    const token = signToken({ userId: user.id, email: user.email });
    return res.json({
      success: true,
      message: "Đăng nhập thành công",
      token,
      user: toUserDto(user)
    });
  });

  router.post("/auth/logout", authMiddleware, (req, res) => res.json(apiOk(null, "Đã đăng xuất")));
}
