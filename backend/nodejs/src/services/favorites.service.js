import { attachDestinationImages, toDestinationDto } from "../shared/dto/destinationDto.js";
import * as favoritesRepository from "../repositories/favorites.repository.js";

export async function listUserFavorites(userId) {
  const rows = await favoritesRepository.listFavoriteDestinationsByUserId(userId);
  const rowsWithImages = await attachDestinationImages(rows);
  return rowsWithImages.map((row) => toDestinationDto(row, true));
}

export async function addUserFavorite(userId, destinationId) {
  const destExists = await favoritesRepository.destinationExists(destinationId);
  if (!destExists) {
    return { ok: false, reason: "destination_not_found" };
  }

  await favoritesRepository.insertFavoriteIgnore(userId, destinationId);
  return { ok: true };
}

export async function removeUserFavorite(userId, destinationId) {
  await favoritesRepository.deleteFavorite(userId, destinationId);
  return { ok: true };
}
