import { db } from "../db.js";

export async function getUserById(id) {
  const user = await db.get(
    "SELECT id, full_name, email, phone, avatar, preferences_json, created_at FROM users WHERE id = ?",
    [id]
  );

  return user ?? null;
}

export async function getUserIdByEmail(email) {
  return db.get("SELECT id FROM users WHERE email = ?", [email]);
}

export async function createUser({ fullName, email, passwordHash, phone, avatar, preferencesJson }) {
  return db.run(
    "INSERT INTO users (full_name, email, password_hash, phone, avatar, preferences_json) VALUES (?, ?, ?, ?, ?, ?)",
    [fullName, email, passwordHash, phone ?? null, avatar ?? null, preferencesJson]
  );
}

export async function getUserProfileById(id) {
  return db.get("SELECT id, full_name, email, phone, avatar, preferences_json, created_at FROM users WHERE id = ?", [
    id
  ]);
}

export async function getUserByEmailWithPasswordHash(email) {
  return db.get(
    "SELECT id, full_name, email, password_hash, phone, avatar, preferences_json, created_at FROM users WHERE email = ?",
    [email]
  );
}

export async function getUserIdByEmailExcludingUser({ email, userId }) {
  return db.get("SELECT id FROM users WHERE email = ? AND id != ?", [email, userId]);
}

export async function updateUserProfile({ userId, fullName, email, phone, avatar, preferencesJsonOrNull }) {
  await db.run(
    "UPDATE users SET full_name = ?, email = ?, phone = ?, avatar = ?, preferences_json = COALESCE(?, preferences_json) WHERE id = ?",
    [fullName, email, phone ?? null, avatar ?? null, preferencesJsonOrNull, userId]
  );
}

export async function updateUserPreferences({ userId, preferencesJson }) {
  await db.run("UPDATE users SET preferences_json = ? WHERE id = ?", [preferencesJson, userId]);
}

export async function updateUserAvatar({ userId, avatarUrl }) {
  await db.run("UPDATE users SET avatar = ? WHERE id = ?", [avatarUrl, userId]);
}

export async function countItinerariesByUserId(userId) {
  return db.get("SELECT COUNT(*) as count FROM itineraries WHERE user_id = ?", [userId]);
}

export async function countFavoritesByUserId(userId) {
  return db.get("SELECT COUNT(*) as count FROM favorites WHERE user_id = ?", [userId]);
}

export async function countReviewsByUserId(userId) {
  return db.get("SELECT COUNT(*) as count FROM reviews WHERE user_id = ?", [userId]);
}
