# Phase 3A — RAG / backend AI alignment with v2 database

Backend and documentation alignment for **Node AI paths** and **RAG contract clarity** against the v2 model (`app_places`, `place_id_map`). Android public routes and JSON response shapes are **unchanged**.

## What changed

### AI catalog (`listDestinationsForAiSuggestion`)

- **Source table:** `destinations` → **`app_places`**.
- **Columns (unchanged):** `id`, `name`, `category`, `rating`, `latitude`, `longitude`, `tags_json`.
- **`ORDER BY id ASC`:** Added so the first 50 rows used in the suggest-itinerary prompt (`.slice(0, 50)` in `ai.service.js`) are **deterministic**. Previously the query had no `ORDER BY`, so which 50 rows appeared depended on the engine’s undefined row order. With the same underlying id set as the legacy catalog (first v2 cut: `app_places.id = destinations.id`), ordering by primary key mainly **stabilizes** behavior rather than inventing new ids; the **first 50 lowest ids** may still differ from a past undefined order in edge cases.
- **No `WHERE is_active = 1`:** Not added, to avoid silently shrinking the catalog vs prior behavior (Phase 2C audit flagged this as a deliberate behavior change).

**Why `app_places`:** Local and v2-target databases (`unudata_v2_test`, migrated `unudata`) expose **`app_places`** as the app-facing place table; ratings/categories follow v2 rules (e.g. review-derived rating per migration 006). Legacy DBs **without** `app_places` will fail this query until migrations are applied—same class of failure already documented for a future switch in `PHASE_2C_AI_CATALOG_AUDIT.md`.

### RAG Python

- **Docstring only** in `get_numeric_destination_id` (`backend/rag/app/ai_itinerary.py`): comments now describe Node resolution via **`place_id_map`**, not `rag_places`. No endpoint URLs, payloads, or retrieval logic were changed.

### Node raw place id mapping

- **No code change required:** `placeIdMap.repository` already maps `rag_place_id` → `new_app_place_id` (aliased as `destination_id` for itinerary FK compatibility). `itineraries.service.js` and `helpers.resolveDestinationIdsFromSelection` already use it.
- **Unresolved reason string:** Still `"not found in rag_places or destination_id is null"` in `helpers.js` for client/API compatibility (Phase 2C decision retained).

## What remained unchanged

- **Public API paths:** e.g. `/api/ai/suggest-itinerary`, `/api/itineraries/create-from-option`, `/api/itineraries/create-from-selection` (Android `ApiService.kt` contracts).
- **Response envelopes** for those routes (routes still own HTTP wiring).
- **RAG runtime behavior:** FastAPI routes, pipeline, JSON files for itinerary options/preview; Node still proxies the same URLs and bodies via `ragClient.js`.
- **`itinerary_items.destination_id` semantics:** Still stores the numeric place id; in v2 first cut this equals **`app_places.id`** (same values as legacy `destinations.id`).
- **Transaction semantics** for suggest-itinerary (route-level transaction in `ai.routes.js` unchanged).

## RAG runtime status

- Python RAG continues to load places from **JSON exports** (`places_app_reviewed.json` / `places_app_file`) for itinerary helpers, not from Node’s MySQL catalog.
- Node **`/ai/suggest-itinerary`** builds its prompt from **MySQL `app_places`** only; it does not call RAG for that flow except on local-AI failure (existing fallback).

## Android contract status

- **Unchanged:** No Android edits. Endpoints and response shapes used by `ApiService.kt` for suggest-itinerary and create-from-option/selection are preserved.

## Known deferred items

| Item | Notes |
|------|--------|
| **Legacy DB without `app_places`** | Operators must use a v2-capable DB (e.g. `unudata_v2_test`) or apply migrations before relying on suggest-itinerary. |
| **Unresolved copy vs `place_id_map`** | User-visible `reason` string still references `rag_places` intentionally. |
| **`/ai/suggest-itinerary` route SQL** | Still inserts into `itineraries` / `itinerary_days` / `itinerary_items` inside the route (pre-existing); not refactored in this phase. |
| **Catalog parity audits** | Full destinations vs `app_places` field diffs (rating/category) deferred to data QA; Phase 3A assumes v2 population per repo migrations. |
| **Optional env-based catalog source** | No feature flag to fall back to `destinations`; could be added later if dual-DB support is required. |

## Smoke test checklist

Prerequisites: Node backend, MySQL with **`app_places`** populated, RAG up if testing RAG-backed flows.

1. **`POST /api/ai/suggest-itinerary`** (auth): Valid preferences + dates → `success: true`, itinerary object with expected shape; DB rows in `itineraries` / `itinerary_days` / `itinerary_items` with `destination_id` values that exist in `app_places` (or legacy equivalent id).
2. **`POST /api/itineraries/create-from-option`** (auth): Body from RAG tour option with mix of `destinationId` and `rawPlaceId` → `success: true` when `place_id_map` covers raw ids; `400` + `no_mapped_destinations` when none resolve (unchanged semantics).
3. **`POST /api/itineraries/create-from-selection`** (auth): Same as above for selection payload.
4. **RAG (optional):** `POST` to FastAPI `/rag/chat/simple` or `/ai/itinerary-options` via Node proxies → same status codes and shapes as before.

## Verification commands (local)

```bash
node --check backend/nodejs/src/repositories/ai.repository.js
node --check backend/nodejs/src/services/ai.service.js
node --check backend/nodejs/src/routes/ai.routes.js
```

```bash
rg "rag_places" backend/nodejs/src --glob "*.js"
```

Expect **`helpers.js` only** for the unresolved-reason string (no SQL against `rag_places` in the Node AI mapping path).

---

*Phase 3A — docs checkpoint; does not replace production runbooks.*
