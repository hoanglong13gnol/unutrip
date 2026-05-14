import bcrypt from "bcryptjs";
import { z } from "zod";
import { apiOk } from "../../utils.js";
import { signToken } from "../../auth.js";
import { toUserDto } from "../../shared/dto/userDto.js";
import * as usersRepository from "../../repositories/users.repository.js";

export async function register(req, res) {
  const schema = z.object({
    fullName: z.string().min(1),
    email: z.string().email(),
    password: z.string().min(4),
    phone: z.string().optional().nullable()
  });

  const parsed = schema.safeParse(req.body);
  if (!parsed.success) return res.status(400).json({ success: false, message: "Invalid payload" });
  const { fullName, email, password, phone } = parsed.data;

  const exists = await usersRepository.getUserIdByEmail(email);
  if (exists) return res.status(400).json({ success: false, message: "Email đã tồn tại" });

  const passwordHash = bcrypt.hashSync(password, 10);
  const info = await usersRepository.createUser({
    fullName,
    email,
    passwordHash,
    phone: phone ?? null,
    avatar: null,
    preferencesJson: JSON.stringify([])
  });

  const user = await usersRepository.getUserProfileById(info.lastInsertRowid);

  const token = signToken({ userId: user.id, email: user.email });

  return res.json({
    success: true,
    message: "Đăng ký thành công",
    token,
    user: toUserDto(user)
  });
}

export async function login(req, res) {
  const schema = z.object({
    email: z.string().email(),
    password: z.string().min(1)
  });

  const parsed = schema.safeParse(req.body);
  if (!parsed.success) return res.status(400).json({ success: false, message: "Invalid payload" });
  const { email, password } = parsed.data;

  const user = await usersRepository.getUserByEmailWithPasswordHash(email);
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
}

export function logout(req, res) {
  return res.json(apiOk(null, "Đã đăng xuất"));
}
