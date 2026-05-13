# V2 Backend DB Adaptation Plan

## Scope and constraints

- Backend adaptation planning only (no code changes in this phase).
- Keep Android API response contract compatible.
- Database migrations are already validated on `unudata_v2_test`.
- Legacy tables still exist, so migration can be phased safely.

## Current backend dependency summary

Primary runtime route dependencies in `backend/nodejs/src/routes`:

- `destinations`:
  - `destinations.routes.js` (`/destinations`, `/destinations/featured`, `/destinations/nearby`, `/destinations/:id`)
  - `favorites.routes.js` (favorites list join + existence check before insert)
  - `reviews.routes.js` (destination existence check + post-review aggregate update)
  - `itineraries.routes.js` (join `itinerary_items.destination_id -> destinations` for itinerary detail)
  - `ai.routes.js` (load destination catalog for prompt context)
- `destination_images`:
  - `helpers.js` `attachDestinationImages()` uses only `status='active'` rows.
- `rag_places`:
  - `helpers.js` `resolveDestinationIdsFromSelection()` maps `rawPlaceId -> destination_id`.
  - `ai.routes.js` create-from-option path maps `rawPlaceId -> destination_id`.

Secondary/admin dependencies in `src/admin.js`:

- Dashboard counts/stats and CRUD currently read/write `destinations` directly.

## Target v2 table usage model

- App-facing place reads: `app_places`
- Runtime images: `place_images`
- RAG knowledge reads (backend-side SQL if needed): `rag_knowledge_base`
- Cross-id resolution (`rawPlaceId`, aliases): `place_id_map`

## Safe rollout strategy

### Phase 1: Introduce data-access abstraction (no API shape changes)

- Add repository/query-layer functions (or equivalent service helpers) for:
  - list/get places
  - featured/nearby places
  - destination image attachment
  - rawPlaceId resolution
  - existence checks for destination-linked writes (favorites/reviews/itinerary items)
- Keep route handlers and DTO serializers unchanged.
- Keep `toDestinationDto()` contract unchanged.

### Phase 2: Switch read paths to v2 sources

- Replace `destinations` reads with `app_places`.
- Replace `destination_images` reads with `place_images`.
- Replace `rag_places` id mapping with `place_id_map` (prefer), then fallback path as needed.
- Maintain existing SQL result aliases so route code can stay stable (`destination_id`, `is_favorite`, etc.).

### Phase 3: Update write-side consistency logic

- Favorites/reviews/itinerary inserts can keep `destination_id` values because ids are reused.
- Destination existence checks should query `app_places`.
- Review aggregate update should target `app_places.rating` and `app_places.review_count` (derived from reviews).
- Stop writing aggregate fields to legacy `destinations`.

### Phase 4: Validation and cutover controls

- Add backend-side dual-read verification mode (temporary):
  - compare key response fields from legacy vs v2 source for sampled requests.
- Add route-level smoke checks:
  - list/detail/featured/nearby/favorites/itinerary detail
  - AI selection rawPlaceId mapping success rate
- Keep controlled fallback toggle to legacy query paths until parity confidence is high.

## Recommended compatibility approach

Two safe options:

- **Preferred: Repository/query layer in Node**
  - Pros: explicit mapping, easier unit testing, avoids hidden DB coupling, clearer rollback.
  - Cons: more application code changes than SQL views.
- **Alternative: DB compatibility views**
  - Create read-only views that mimic legacy table columns using v2 tables.
  - Pros: minimal JS query changes initially.
  - Cons: less explicit behavior, harder to evolve, may hide performance issues.

Recommendation: implement repository layer first; optionally add temporary compatibility views only for high-risk endpoints.

## High-risk areas to handle carefully

- `rawPlaceId` resolution:
  - must move from `rag_places.place_id -> destination_id` to `place_id_map` coverage.
- Image ordering/primary behavior:
  - `attachDestinationImages()` currently relies on `ORDER BY is_primary DESC, id ASC`.
  - ensure equivalent ordering semantics on `place_images`.
- Aggregate rating updates:
  - ensure no stale writes to `destinations.rating` after cutover.
- Nearby query:
  - preserve numeric lat/lng fields and sorting behavior.

## Proposed implementation order (backend)

1. Introduce repository functions + feature flag.
2. Migrate `helpers.attachDestinationImages()` to `place_images`.
3. Migrate `destinations.routes.js` read queries to `app_places`.
4. Migrate `favorites.routes.js` and `itineraries.routes.js` joins/existence checks.
5. Migrate `reviews.routes.js` destination existence + aggregate update target.
6. Migrate `helpers.resolveDestinationIdsFromSelection()` and AI route mapper to `place_id_map`.
7. Migrate admin queries to v2 (if admin is in scope for this release).

## Success criteria

- Android-facing responses remain shape-compatible.
- Row-level behavior parity for list/detail/nearby/favorites/itinerary detail endpoints.
- No increase in unresolved `rawPlaceId` mapping errors.
- No regressions in review aggregates and image rendering behavior.

