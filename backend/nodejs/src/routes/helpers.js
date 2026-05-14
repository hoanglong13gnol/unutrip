/**
 * Phase 5 / Phase 8 compatibility shim — implementation lives in
 * `src/shared/dto/{user,destination,itinerary}Dto.js`.
 * Kept as a re-export so any external import of this path keeps working.
 */
export {
  toUserDto,
  getUserById,
  firstArrayValue
} from "../shared/dto/userDto.js";
export {
  attachDestinationImages,
  fixUrl,
  normalizeCategoryParam,
  toDestinationDto
} from "../shared/dto/destinationDto.js";
export {
  flattenSelectedOptionDays,
  itineraryRowToDto,
  resolveDestinationIdsFromSelection
} from "../shared/dto/itineraryDto.js";
