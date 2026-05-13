# Legacy to V2 Query Map

This document maps current backend SQL usage to planned v2 equivalents.

## Legend

- Legacy app table: `destinations`
- V2 app table: `app_places`
- Legacy image table: `destination_images`
- V2 image table: `place_images`
- Legacy RAG id map source: `rag_places`
- V2 id map source: `place_id_map`

## 1) `destinations.routes.js`

### `/destinations` list

Current:

- Count: `SELECT COUNT(*) FROM destinations ...`
- Data: `SELECT d.*, EXISTS(...) as is_favorite FROM destinations d ... ORDER BY d.rating ...`

V2:

- Count/data base table: `app_places d`
- Favorites join logic unchanged (`favorites.destination_id = d.id`)
- Keep `d.*` fields aligned with `toDestinationDto()` expectations.

### `/destinations/featured`

Current:

- `SELECT d.*, EXISTS(...) as is_favorite FROM destinations d ORDER BY d.rating DESC, d.review_count DESC LIMIT 5`

V2:

- Replace `destinations` with `app_places`.
- Preserve ordering fields (`rating`, `review_count`).

### `/destinations/nearby`

Current:

- Haversine query on `destinations.latitude/longitude`, plus favorite EXISTS.

V2:

- Same SQL shape against `app_places`.
- Preserve `distance_km` alias and downstream `distanceKm` response mapping.

### `/destinations/:id`

Current:

- `SELECT d.*, EXISTS(...) as is_favorite FROM destinations d WHERE d.id = ?`

V2:

- Replace with `app_places d`.

## 2) `helpers.js`

### `attachDestinationImages()`

Current:

- `SELECT destination_id, image_url FROM destination_images WHERE status='active' AND destination_id IN (...) ORDER BY is_primary DESC, id ASC`

V2:

- `SELECT app_place_id as destination_id, image_url FROM place_images WHERE status='active' AND app_place_id IN (...) ORDER BY is_primary DESC, id ASC`
- Keep alias `destination_id` so current mapper logic remains compatible.

### `resolveDestinationIdsFromSelection()`

Current:

- `SELECT destination_id FROM rag_places WHERE place_id = ? LIMIT 1`

V2 preferred:

- `SELECT new_app_place_id AS destination_id FROM place_id_map WHERE rag_place_id = ? LIMIT 1`

Fallback option:

- If no `rag_place_id` match, optionally attempt canonical/alias `place_key` lookups in `place_id_map`.

## 3) `favorites.routes.js`

### Favorites list

Current:

- `FROM favorites f JOIN destinations d ON d.id = f.destination_id`

V2:

- `JOIN app_places d ON d.id = f.destination_id`

### Destination existence check before add

Current:

- `SELECT id FROM destinations WHERE id = ?`

V2:

- `SELECT id FROM app_places WHERE id = ?`

## 4) `reviews.routes.js`

### Destination existence check before review insert

Current:

- `SELECT id FROM destinations WHERE id = ?`

V2:

- `SELECT id FROM app_places WHERE id = ?`

### Aggregate write after insert

Current:

- Aggregate from `reviews`, then:
- `UPDATE destinations SET rating = ?, review_count = ? WHERE id = ?`

V2:

- Keep aggregate source: `reviews` (unchanged, required rule).
- Update target: `app_places`.
- Do not treat `rag_places.quality_score` as app rating source.

## 5) `itineraries.routes.js`

### Itinerary detail destination join

Current:

- `JOIN destinations d2 ON d2.id = ii.destination_id`

V2:

- `JOIN app_places d2 ON d2.id = ii.destination_id`

### Note on writes

- Inserts into `itinerary_items.destination_id` can remain unchanged because ids are reused in v2.

## 6) `ai.routes.js`

### `/ai/suggest-itinerary` destination catalog load

Current:

- `SELECT id, name, category, rating, latitude, longitude, tags_json FROM destinations`

V2:

- Same projection from `app_places`.

### `create-from-option` rawPlaceId mapping

Current:

- `SELECT destination_id FROM rag_places WHERE place_id = ? LIMIT 1`

V2:

- `SELECT new_app_place_id AS destination_id FROM place_id_map WHERE rag_place_id = ? LIMIT 1`

### `create-from-selection` path

- Uses helper resolver; migrate resolver once and this path follows.

## 7) `admin.js` (non-Android, but backend usage)

Current `destinations` dependencies:

- Dashboard counts/statistics
- Destination list/detail
- Destination CRUD (insert/update/delete)
- Category/rating statistics

V2 recommendation:

- Migrate read paths to `app_places`.
- Decide whether admin CRUD should mutate `app_places` only or dual-write during transition.

## 8) No current backend SQL usage found

- `rag_knowledge_base` direct SQL usage: none in current Node routes.
- `place_images` direct SQL usage: none (yet).
- `place_id_map` direct SQL usage: none (yet).

## 9) Compatibility notes for query rewrites

- Preserve column names consumed by DTO functions:
  - snake_case source fields used by `toDestinationDto()`:
    `review_count`, `open_time`, `close_time`, `entry_fee`, `tags_json`
- Preserve favorite alias:
  - `is_favorite`
- Preserve image attach shape:
  - `destination_id` alias expected in helper map.

