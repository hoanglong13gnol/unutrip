import { db } from "../db.js";

export async function getUserById(id) {
  const user = await db.get(
    "SELECT id, full_name, email, phone, avatar, preferences_json, created_at FROM users WHERE id = ?",
    [id]
  );

  return user ?? null;
}
