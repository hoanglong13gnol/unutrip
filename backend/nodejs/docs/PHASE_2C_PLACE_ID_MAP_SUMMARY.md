# Phase 2C — place_id_map checkpoint

Checkpoint documentation for raw place id resolution moving from legacy `rag_places` SQL in Node to **`place_id_map`**, without changing HTTP routes, Android contracts, or RAG runtime.

## What changed

| Area | Before | After |
|------|--------|--------|
| **Mapping repository** | `ragPlaces.repository.js` queried `rag_places` | **`placeIdMap.repository.js`** added; queries `place_id_map` |
| **`resolveDestinationIdsFromSelection`** (`helpers.js`) | Resolved raw ids via `rag_places` | Resolves **`rawPlaceId` / `raw_place_id` / `placeId` / `place_id`** through **`place_id_map`** via `placeIdMapRepository` |
| **`createItineraryFromAiOption` second pass** (`itineraries.service.js`) | Built `destinationIdByRawPlaceId` via `ai.repository` → `rag_places` | Uses **`placeIdMapRepository`** → **`place_id_map`** |
| **`ai.repository.js`** | Exported legacy `getDestinationIdByRagPlaceId` (`rag_places`) | **Removed**; no `rag_places` lookup in this module |
| **`ragPlaces.repository.js`** | Standalone `rag_places` reader | **Removed** / **confirmed absent** (dead code eliminated) |

## Mapping

- **`rag_places.place_id`** equivalent → **`place_id_map.rag_place_id`** (client raw / Google-style id string).
- **`rag_places.destination_id`** equivalent → **`place_id_map.new_app_place_id`** (app place id; first v2 cut aligned with legacy `destinations.id`).
- **`placeIdMap.repository`**: SQL selects `new_app_place_id AS destination_id` and returns a **destination-id–compatible scalar** (`number` / `null`) for drop-in use with `itinerary_items.destination_id` and existing DTOs.

## Behavior preserved

- **Direct `destinationId`** (and `destination_id`) is still preferred when valid (positive integer).
- **Raw id aliases** `rawPlaceId`, `raw_place_id`, `placeId`, `place_id` are still supported.
- **Unresolved reason strings** are unchanged, including:
  - `"not found in rag_places or destination_id is null"`
- **`destinationIds` dedupe**: `[...new Set(resolvedIds)]` in `resolveDestinationIdsFromSelection` unchanged.
- **`selectedCount`**: create-from-option uses inserted row count; create-from-selection uses resolved/id-list length — unchanged.
- **create-from-option partial insert**: items without a resolvable id are skipped; itinerary may still be created when at least one id resolves — unchanged.
- **create-from-selection**: `selectedDestinationIds` vs `selectedDestinations` branches unchanged.
- **400 response bodies** for `no_mapped_destinations` and `invalid_dates` unchanged.

## Unchanged

- **RAG runtime** (FastAPI / retriever behavior) unchanged.
- **RAG Python** unchanged.
- **Android response contract** unchanged.
- **`POST /itineraries/create-from-option`** and **`POST /itineraries/create-from-selection`** route handlers unchanged (only underlying resolution source moved).
- **Transaction vs non-transaction** behavior for these flows unchanged (create-from flows remain non-transactional as before).
- **`itinerary_items.destination_id` semantics** unchanged (still app place id space).
- **`admin.js`** remains deferred.

## Known risks

| Risk | Notes |
|------|--------|
| **`place_id_map` coverage** | Must match or exceed prior **`rag_places`** resolution for the same `rag_place_id` values; gaps surface as `no_mapped_destinations` or partial inserts. |
| **Unresolved copy** | String still says **`rag_places`** intentionally for API/client compatibility even though resolution uses **`place_id_map`**. |
| **`selectedDestinationIds` path** | Bypasses raw-id mapping entirely; unchanged — invalid ids still fail at insert or downstream, not via `place_id_map`. |
| **`listDestinationsForAiSuggestion`** | Still reads **`destinations`** in `ai.repository.js`; separate migration/audit before switching catalog to **`app_places`**. |

## Smoke test checklist

Run against an environment with **`place_id_map`** populated as expected.

- [ ] **POST `/itineraries/create-from-selection`** with **`selectedDestinations`** (raw ids / mixed with direct ids).
- [ ] **POST `/itineraries/create-from-selection`** with **`selectedDestinationIds`** only.
- [ ] **POST `/itineraries/create-from-option`** with multi-day **`days`** / items.
- [ ] **`no_mapped_destinations`** → **400** with expected `data` shape (`optionId` / `unresolved` vs `receivedSelectedDestinations` / `receivedSelectedDestinationIds`).
- [ ] **Successful** itinerary + **`itinerary_items`** rows for resolved ids; **`selectedCount`** matches expectations.

## Recommended next phase

1. **Audit** `ai.repository.listDestinationsForAiSuggestion()` — currently **`SELECT ... FROM destinations`**; confirm whether AI suggestion / prompt context should read **`app_places`** instead for parity with Phase 2B place reads.
2. **Decide** catalog cutover policy: **`destinations` → `app_places`** for AI listing only when contract and column alignment are verified.
3. **Do not** change RAG runtime or Python ingestion until mapping and Node proxy contracts are explicitly in scope for that phase.

---

*Checkpoint only; does not replace migration runbooks or full regression suites.*
