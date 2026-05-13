# API Compatibility Checklist (Android Contract)

Use this checklist while adapting backend DB reads from legacy to v2.

## Core response contract to preserve

Primary destination DTO is produced by `toDestinationDto()` and must stay stable:

- `id`
- `name`
- `description`
- `address`
- `city`
- `province`
- `latitude`
- `longitude`
- `category`
- `images` (array)
- `rating` (number)
- `reviewCount` (number)
- `openTime`
- `closeTime`
- `entryFee`
- `tags` (array)
- `isFavorite` (boolean)

## Endpoint compatibility checks

## `/destinations`

- Response envelope unchanged: `{ success, data, total, page, limit }`
- `data[]` shape equals destination DTO.
- Filtering behavior unchanged for `category`, `province`, `search`.
- Pagination behavior unchanged.

## `/destinations/featured`

- Response envelope unchanged: `{ success, data, total, page, limit }`
- Ordered by rating/review quality semantics unchanged.

## `/destinations/nearby`

- Response envelope unchanged:
  - `{ success, data, total, page, limit, center, radiusKm }`
- Each item keeps all destination DTO fields plus:
  - `distanceKm` (number)

## `/destinations/:id`

- Response envelope unchanged: `{ success, data }`
- `404` behavior unchanged for missing id.

## `/users/favorites` (GET/POST/DELETE)

- GET returns destination DTO list unchanged.
- POST/DELETE success envelope unchanged (`apiOk` / `{ success: true, ... }` behavior).

## `/destinations/:id/reviews` and `/reviews`

- GET review item fields unchanged:
  - `id`, `userId`, `userName`, `userAvatar`, `destinationId`, `rating`, `comment`, `images`, `createdAt`
- POST review response field names unchanged.
- Review-created aggregate behavior still reflected in destination reads (now from v2 target table).

## `/itineraries` and `/itineraries/:id`

- Itinerary envelope shape unchanged.
- In detail response, nested item keeps:
  - `destinationId`
  - `destination` object in destination DTO shape.

## AI-assisted itinerary creation endpoints

- Any path accepting `destinationId` and/or `rawPlaceId` keeps request compatibility.
- Error messages for unresolved mapping should remain semantically consistent.

## Data behavior compatibility checks

- `rating` and `reviewCount` remain numeric in API output (no nulls).
- `images` fallback behavior preserved:
  - primary source: active image table rows
  - fallback: JSON field parsing only if needed by helper logic.
- Category values remain within expected Android set (plus tolerated `other` if present).
- Favorite flag behavior unchanged (`isFavorite` based on current user).

## Migration-specific checks (v2 backing)

- Destination read paths source `app_places` without API shape change.
- Image attachment sources `place_images` with same output semantics.
- Raw-place id resolution uses `place_id_map` and does not reduce mapping coverage.
- Nearby query still returns similar ordering and distance behavior.

## Verification workflow (recommended)

- Snapshot current API responses from legacy-backed branch for representative requests.
- Run same requests on v2-backed branch.
- Compare:
  - JSON keys/types
  - nullability
  - ordering for deterministic endpoints
  - list lengths and id presence for the same filters.
- Validate authenticated flows (`isFavorite`) with seeded user data.

## Pass criteria

- No Android-facing contract-breaking field/name/type changes.
- No increase in unresolved rawPlaceId mapping failures.
- No regressions in destination list/detail/favorites/itinerary rendering behavior.

