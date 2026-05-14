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

/** Cập nhật user từ admin. `passwordHash` null/undefined = giữ mật khẩu cũ. */
export async function adminUpdateUser({ userId, fullName, email, phone, passwordHash }) {
  if (passwordHash) {
    await db.run(
      "UPDATE users SET full_name = ?, email = ?, phone = ?, password_hash = ? WHERE id = ?",
      [fullName, email, phone ?? null, passwordHash, userId]
    );
  } else {
    await db.run("UPDATE users SET full_name = ?, email = ?, phone = ? WHERE id = ?", [
      fullName,
      email,
      phone ?? null,
      userId
    ]);
  }
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

/**
 * Admin-scoped detail lookup used by `GET /admin/users/api/:id`.
 *
 * Phase 4 pilot — preserves the exact column projection, table, and
 * `WHERE id = ?` shape of the previous inline `db.get` call so the JSON
 * payload returned to the admin UI is byte-identical (including the case
 * where the row is missing — `db.get` resolves to `undefined`, which the
 * admin handler then translates to a 404).
 */
export async function getAdminUserDetailById(id) {
  return db.get(
    "SELECT id, full_name, email, phone, avatar, preferences_json, created_at FROM users WHERE id = ?",
    [id]
  );
}

/**
 * Admin-scoped DELETE used by `POST /admin/users/delete/:id`.
 *
 * Phase 4 pilot — the inline DELETE relied on FK constraints to cascade
 * to `favorites` / `reviews` / `itineraries`, which is documented in the
 * admin UI's confirm prompt. SQL text is preserved verbatim.
 */
export async function deleteUserById(id) {
  return db.run("DELETE FROM users WHERE id = ?", [id]);
}
