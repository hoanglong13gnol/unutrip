# Phase 2B Place Switch Summary

Checkpoint documentation for the Phase 2B segment that aligned Android-facing place **reads** and review-driven **aggregates** with v2 app tables, without changing HTTP contracts, RAG runtime, or AI itinerary persistence flows.

## 1. What changed

| Area | Before | After |
|------|--------|--------|
| **Destination image reads** | `destination_images` (`destination_id`, `image_url`, …) | `place_images` with `app_place_id AS destination_id` so downstream mappers keep the same row shape |
| **Destination reads** (list, featured, nearby, by id) | `destinations` | `app_places` (same query shape: `d.*`, `is_favorite`, `distance_km` where applicable) |
| **Favorites list and existence** | `JOIN destinations` / `SELECT id FROM destinations` | `JOIN app_places` / `SELECT id FROM app_places` |
| **Review destination existence** | `SELECT id FROM destinations` | `SELECT id FROM app_places` |
| **Review aggregate write target** | `UPDATE destinations SET rating, review_count` | `UPDATE app_places SET rating, review_count` (aggregate **values** still computed from `reviews`) |

Repository implementations:

- `backend/nodejs/src/repositories/destinationImages.repository.js`
- `backend/nodejs/src/repositories/destinations.repository.js`
- `backend/nodejs/src/repositories/favorites.repository.js`
- `backend/nodejs/src/repositories/reviews.repository.js`

## 2. What remained unchanged

- **API paths** — No URL or method changes for the affected endpoints.
- **Android DTO / response contract** — Same envelopes and field names; serialization still flows through existing helpers (e.g. `toDestinationDto`) and services.
- **Services and routes** — No edits in Phase 2B for this segment; behavior changes are SQL-layer only behind stable repository function signatures.
- **`favorites` table** — Same schema; `INSERT IGNORE` / `DELETE` behavior preserved.
- **`reviews` table** — Same schema; inserts and list queries unchanged.
- **ID semantics** — `favorites.destination_id` and `reviews.destination_id` still reference the app place id space (aligned with `app_places.id` in the first v2 cut).
- **RAG runtime** — FastAPI RAG integration and Node proxy behavior unchanged.
- **AI routes** — Not modified in this segment.
- **create-from-option / create-from-selection** — Not modified; still use existing resolution paths.
- **`rag_places` / `place_id_map`** — Not switched; raw-place id mapping remains on legacy plan for a later phase.
- **`admin.js`** — Deferred; may still use legacy `destinations` for reads/writes until a dedicated admin pass.

## 3. Files changed in this Phase 2B segment

1. `backend/nodejs/src/repositories/destinationImages.repository.js`
2. `backend/nodejs/src/repositories/destinations.repository.js`
3. `backend/nodejs/src/repositories/favorites.repository.js`
4. `backend/nodejs/src/repositories/reviews.repository.js`

## 4. Compatibility assumptions

These assumptions must hold for correct behavior:

- **`app_places.id`** matches the legacy **`destinations.id`** values used by clients and foreign keys (first v2 population model).
- **`place_images.app_place_id`** matches **`app_places.id`** for image attachment by place id.
- **`favorites.destination_id`** and **`reviews.destination_id`** remain valid references into the **`app_places`** id space (same integers as before for migrated data).

If any environment drifts (missing `app_places` rows, partial image migration), list/detail/favorites/reviews behavior will diverge from expectations even though the API shape stays the same.

## 5. Known risks

| Risk | Impact |
|------|--------|
| **`app_places` has no `images_json`** | `toDestinationDto` can no longer fall back to legacy JSON on rows loaded only from `app_places`; images depend on `place_images` (and any pre-attached table data). |
| **Places without `place_images` rows** | May return **empty `images`** arrays even if legacy `destinations.images_json` had URLs. |
| **Stale legacy `destinations` aggregates** | After review aggregate writes target **`app_places`**, legacy **`destinations.rating` / `review_count`** are no longer updated by this path and may go stale. Anything still reading legacy `destinations` (e.g. admin) can disagree with the Android API. |
| **Admin deferred** | `admin.js` may still assume legacy tables until refactored; operational confusion if compared to production API data. |

## 6. Smoke test checklist

Run against a database where v2 place and image migrations have been applied as expected.

- [ ] **`GET /health`** — Backend up.
- [ ] **`GET /destinations`** — Paginated list; filters if used; `total` consistent with list; DTO fields present.
- [ ] **`GET /destinations/featured`** — Short list; ordering sensible.
- [ ] **`GET /destinations/nearby`** — Valid `lat`/`lng`; `distanceKm` present; invalid coords still `400`.
- [ ] **`GET /destinations/:id`** — Known id returns DTO; unknown id `404`.
- [ ] **`GET /users/favorites`** (authenticated) — Destination DTO list; images and `isFavorite` where applicable.
- [ ] **`POST /reviews`** (or route used for creating reviews) — Valid `destinationId` succeeds; invalid id rejected; then **`GET /destinations/:id`** (or detail path) shows updated **`rating`** / **`reviewCount`** aligned with aggregates on **`app_places`**.

## 7. Recommended next phase

1. **Itinerary detail and persistence** — Audit joins and existence checks that still reference **`destinations`** (e.g. itinerary item → place enrichment). Align reads with **`app_places`** where the Android contract expects the same destination DTO, without changing response shapes.
2. **AI id mapping** — Plan a **separate** migration from **`rag_places`** to **`place_id_map`** for `rawPlaceId` resolution and related paths; do **not** switch RAG service runtime or contracts until that plan is executed and tested.
3. **Admin** — Schedule legacy **`destinations`** cleanup or dual-read/dual-write policy when admin scope is approved.

---

*This document is a checkpoint only; it does not replace migration runbooks or environment-specific validation.*
