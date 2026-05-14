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

/**
 * Phase 7 — duplicate-email checks for `POST /admin/users/save` before password rules run
 * (create path must return “Email đã tồn tại” even when the new password is invalid).
 *
 * @param {{ idNum: number, email: string }} p
 * @returns {Promise<{ ok: true } | { ok: false, reason: "email_in_use_other" | "email_exists" }>}
 */
export async function adminAssertEmailAvailableForSave({ idNum, email }) {
  if (Number.isFinite(idNum) && idNum > 0) {
    const dup = await getUserIdByEmailExcludingUser({ email, userId: idNum });
    if (dup) {
      return { ok: false, reason: "email_in_use_other" };
    }
    return { ok: true };
  }
  const dup = await getUserIdByEmail(email);
  if (dup) {
    return { ok: false, reason: "email_exists" };
  }
  return { ok: true };
}

/**
 * Phase 7 — `INSERT` / `UPDATE` for admin user save after email availability and password rules
 * in the route. `passwordHash` null/undefined on update = keep existing password.
 *
 * @param {{ idNum: number, fullName: string, email: string, phone: string | null, passwordHash: string | null }} p
 */
export async function adminPersistUserSave({ idNum, fullName, email, phone, passwordHash }) {
  if (Number.isFinite(idNum) && idNum > 0) {
    await adminUpdateUser({
      userId: idNum,
      fullName,
      email,
      phone,
      passwordHash: passwordHash ?? null
    });
    return;
  }
  await createUser({
    fullName,
    email,
    passwordHash,
    phone,
    avatar: null,
    preferencesJson: JSON.stringify([])
  });
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

/**
 * Admin-scoped listing used by `GET /admin/users` (no-search variant).
 *
 * Phase 5 continuation of the Phase 4 pilot — SQL string is byte-identical
 * to the previous inline `db.query` call. The column projection is
 * consumed directly by the rendered admin HTML (template renders fields
 * by their exact column name), so do NOT change which columns are
 * selected or their order.
 */
export async function listAdminUsers() {
  return db.query(
    "SELECT id, full_name, email, phone, created_at FROM users ORDER BY created_at DESC"
  );
}

/**
 * Admin-scoped 4-column LIKE search used by `GET /admin/users?q=…`.
 *
 * Phase 5 continuation of the Phase 4 pilot — SQL is byte-identical to
 * the previous inline `db.query` call, including the 11-space leading
 * indentation on the continuation lines (kept so the SQL string content
 * is preserved exactly, not just visually). Caller passes the
 * already-`%…%`-wrapped `like` string; this repo function does NOT wrap
 * it (matches the pre-Phase-5 contract).
 */
export async function searchAdminUsers({ like }) {
  return db.query(
    `SELECT id, full_name, email, phone, created_at FROM users
           WHERE full_name LIKE ? OR email LIKE ? OR IFNULL(phone,'') LIKE ? OR CAST(id AS CHAR) LIKE ?
           ORDER BY created_at DESC`,
    [like, like, like, like]
  );
}
