/**
 * User DTO module — Phase 5 split of `src/routes/helpers.js`.
 *
 * Function bodies are byte-identical copies of the originals.
 * `fixUrl` is imported from the destination DTO because it is shared
 * between the two DTOs and lives there.
 */

import { parseJsonArray } from "../../utils.js";
import * as usersRepository from "../../repositories/users.repository.js";
import { fixUrl } from "./destinationDto.js";

export function toUserDto(row) {
  return {
    id: row.id,
    fullName: row.full_name,
    email: row.email,
    phone: row.phone ?? null,
    avatar: fixUrl(row.avatar),
    preferences: parseJsonArray(row.preferences_json, []),
    createdAt: row.created_at ?? null
  };
}

export async function getUserById(id) {
  const user = await usersRepository.getUserById(id);
  if (!user) throw new Error("User not found");
  return user;
}

export function firstArrayValue(obj) {
  if (!obj || typeof obj !== "object") return null;
  for (const v of Object.values(obj)) {
    if (Array.isArray(v)) return v;
  }
  return null;
}
