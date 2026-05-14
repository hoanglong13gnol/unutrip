import { z } from "zod";
import { apiOk } from "../../utils.js";
import { getUserById, toUserDto, firstArrayValue } from "../../shared/dto/userDto.js";
import * as usersRepository from "../../repositories/users.repository.js";

export async function getProfile(req, res) {
  try {
    const user = await getUserById(req.user.userId);
    return res.json(apiOk(toUserDto(user), "OK"));
  } catch (error) {
    return res.status(404).json({ success: false, message: error.message });
  }
}

export async function getStats(req, res) {
  try {
    const itineraries = await usersRepository.countItinerariesByUserId(req.user.userId);
    const favorites = await usersRepository.countFavoritesByUserId(req.user.userId);
    const reviews = await usersRepository.countReviewsByUserId(req.user.userId);

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
}

export async function updateProfile(req, res) {
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
  const existing = await usersRepository.getUserIdByEmailExcludingUser({ email, userId: req.user.userId });
  if (existing) return res.status(400).json({ success: false, message: "Email đã được dùng" });

  await usersRepository.updateUserProfile({
    userId: req.user.userId,
    fullName,
    email,
    phone: phone ?? null,
    avatar: avatar ?? null,
    preferencesJsonOrNull: preferences ? JSON.stringify(preferences) : null
  });

  const user = await getUserById(req.user.userId);
  return res.json(apiOk(toUserDto(user), "Cập nhật thành công"));
}

export async function updatePreferences(req, res) {
  const body = req.body ?? {};
  const prefs = Array.isArray(body.preferences)
    ? body.preferences
    : Array.isArray(body.preference)
      ? body.preference
      : firstArrayValue(body);

  if (!Array.isArray(prefs)) return res.status(400).json({ success: false, message: "Invalid payload" });
  await usersRepository.updateUserPreferences({
    userId: req.user.userId,
    preferencesJson: JSON.stringify(prefs)
  });
  const user = await getUserById(req.user.userId);
  return res.json(apiOk(toUserDto(user), "OK"));
}

export async function uploadAvatar(req, res) {
  if (!req.file) return res.status(400).json({ success: false, message: "No file uploaded" });
  const avatarUrl = `/uploads/avatars/${req.file.filename}`;
  await usersRepository.updateUserAvatar({ userId: req.user.userId, avatarUrl });
  const user = await getUserById(req.user.userId);
  return res.json(apiOk(toUserDto(user), "Cập nhật ảnh đại diện thành công"));
}
