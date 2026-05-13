# Phase 2B Itinerary Compatibility Summary

Checkpoint documentation for itinerary read and detail behavior after aligning itinerary item **destination enrichment** with v2 **`app_places`** and **nested destination images** with **`place_images`**, without changing HTTP contracts, persistence tables, or RAG/AI mapping plans.

## 1. What changed

| Area | Before | After |
|------|--------|--------|
| **Itinerary item destination enrichment** | `listItineraryItemsWithDestinationByDayId` joined **`destinations d2`** on `d2.id = ii.destination_id` | Same query shape joins **`app_places d2`** (`SELECT ii.*, d2.*`, same `WHERE` / `ORDER BY`) |
| **Itinerary detail nested destination images** | `getItineraryDetailForUser` passed merged rows directly to **`toDestinationDto`** (no `attachDestinationImages`); legacy join could supply **`images_json`** | Service builds synthetic rows with **`id = destination_id`** for **`attachDestinationImages`**, merges **`images_from_table`** back onto each item row, then **`toDestinationDto(i, false)`** — images load from **`place_images`** via existing repository |

## 2. What stayed unchanged

- **API paths** — No URL or method changes for itinerary endpoints.
- **Itinerary response shape** — Same envelopes and nested structure (`itinerary`, `days`, `items`, per-item fields, nested `destination` DTO keys).
- **Tables** — **`itineraries`**, **`itinerary_days`**, **`itinerary_items`** schema and write targets unchanged.
- **`itinerary_items.destination_id` semantics** — Still stores the app-facing place id (same integer space as **`app_places.id`** in the first v2 cut).
- **Create / update / delete itinerary flows** — Repository `INSERT`/`UPDATE`/`DELETE` for itinerary tables unchanged in this segment.
- **create-from-option / create-from-selection** — Not modified; inline persistence and **`rag_places`**-backed resolution unchanged.
- **Transaction behavior** — **`saveAiItinerary`** remains transactional where it was; create-from flows remain non-transactional as before.
- **RAG runtime** — FastAPI RAG integration unchanged.
- **`rag_places` / `place_id_map`** — Not switched; deferred to a dedicated AI id-mapping phase.

## 3. Files changed

1. `backend/nodejs/src/repositories/itineraries.repository.js` — `JOIN app_places d2` in `listItineraryItemsWithDestinationByDayId`.
2. `backend/nodejs/src/services/itineraries.service.js` — `attachDestinationImages` defensive pattern in `getItineraryDetailForUser` before mapping items to DTOs.

## 4. Compatibility assumptions

These must hold for correct itinerary detail behavior:

- **`itinerary_items.destination_id`** references **`app_places.id`** (same ids as legacy **`destinations.id`** after migration).
- **`app_places.id`** stays aligned with the legacy destination id space used when items were created.
- **`place_images.app_place_id`** matches **`app_places.id`** for rows that should appear in nested **`destination.images`**.

## 5. Known risks

| Risk | Notes |
|------|--------|
| **`SELECT ii.*, d2.*` duplicate columns** | Both **`itinerary_items`** and **`app_places`** expose **`id`** (and possibly other name collisions). Flat row objects depend on driver merge rules. |
| **`item.id` vs nested `destination.id`** | After future SQL or driver changes, validate that outer **`item.id`** and nested **`destination.id`** still match product expectations; smoke-test when touching this query. |
| **Defensive attach** | Synthetic **`{ ...row, id: row.destination_id }`** ensures **`place_images`** lookups use the canonical place id regardless of which **`id`** wins on the merged row. |
| **Orphan `destination_id`** | If **`itinerary_items.destination_id`** has no matching **`app_places`** row, the **`JOIN`** drops the item from the day list (item “disappears” from detail). |

## 6. Smoke test checklist / results

Use an authenticated user with at least one itinerary that includes items linked to migrated places.

- [ ] **`GET /itineraries/:id`** returns **`success`** and itinerary payload (or **`404`** when not owned / missing).
- [ ] **`days`** array present; each day has **`items`** when expected.
- [ ] Each item includes **`id`**, **`dayId`**, **`destinationId`**, **`destination`**, **`startTime`**, **`endTime`**, **`note`**, **`orderIndex`**.
- [ ] Nested **`destination`** includes full DTO fields per Android contract (`id`, `name`, `images`, `rating`, `reviewCount`, etc.).
- [ ] **`destination.images`** is non-empty when **`place_images`** has active rows for that **`app_place_id`**; may be empty when no images exist (expected).

*Record pass/fail and sample ids in your environment’s test log when executing this checklist.*

## 7. Recommended next phase

1. **Audit AI / raw place id resolution** — Paths that map **`rawPlaceId` → destination id** still use **`rag_places`** (and related helpers); plan parity and error semantics before cutover.
2. **Plan `rag_places` → `place_id_map`** as a **separate** migration with explicit tests; do not conflate with itinerary CRUD.
3. **Do not switch RAG runtime** until mapping and Node proxy contracts are reviewed and signed off.
4. **Admin** — When in scope, align **`admin.js`** reads/writes away from legacy **`destinations`** if it still assumes pre–Phase 2B tables.

---

*Checkpoint only; does not replace migration runbooks or full regression suites.*
