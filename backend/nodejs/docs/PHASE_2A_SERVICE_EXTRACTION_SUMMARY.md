# Phase 2A Service Extraction Summary

## 1. What Phase 2A achieved

Phase 2A introduced a **service layer** for Android-facing runtime API flows while **keeping behavior and contracts identical** to the pre-refactor implementation. Inline orchestration, multi-step workflows, and RAG or AI proxy calls were moved behind service modules where appropriate. **Routes were thinned** to HTTP concerns: authentication, validation, status codes, and response envelopes. **Repositories** (Phase 1) remained the SQL boundary; Phase 2A did **not** change which legacy tables are read or written, did **not** introduce v2 table cutover, and did **not** change RAG service behavior or Android clients.

## 2. Services now available

All paths are under `backend/nodejs/src/services/`:

| Service | Role (summary) |
|---------|----------------|
| **`favorites.service.js`** | Favorite workflows orchestration on top of `favorites.repository.js`. |
| **`reviews.service.js`** | Review writes and related orchestration on top of `reviews.repository.js`. |
| **`destinations.service.js`** | Destination listing and detail reads via `destinations.repository.js` / related repos. |
| **`itineraries.service.js`** | Itinerary CRUD, transactional AI itinerary save (`saveAiItinerary`), and **non-transactional** AI create-from-option / create-from-selection persistence. |
| **`ai.service.js`** | AI/RAG orchestration without HTTP: itinerary preview/options proxies, RAG chat simple proxy, `/ai/chat` local+RAG fallback helpers, suggest-itinerary **model pipeline** (catalog → prompt → local/RAG → parse), and related helpers. |

## 3. Routes now thinner

These route files delegate business logic to the services above while preserving paths and response shapes:

| Route file | Notes |
|------------|--------|
| **`favorites.routes.js`** | Validation and `res` mapping; service owns workflow. |
| **`reviews.routes.js`** | Same pattern. |
| **`destinations.routes.js`** | Same pattern. |
| **`itineraries.routes.js`** | Same pattern; transactional save remains delegated to `itineraries.service.js`. |
| **`ai.routes.js`** | Zod/auth and HTTP mapping; AI itinerary **suggest** persistence stays in route with explicit transaction; model generation and other proxies call **`ai.service.js`**; create-from-option/selection call **`itineraries.service.js`**. |

## 4. What stayed unchanged

- **API paths** — No URL changes for extracted endpoints.
- **Android response contract** — Envelopes (`success`, `message`, `data`, field names, paging where applicable) preserved.
- **Auth middleware behavior** — Same middleware attachment and ordering per route.
- **Validation and status codes** — Zod and inline checks, **400** / **500** / **502** semantics preserved where applicable.
- **Legacy DB tables** — Runtime still uses `destinations`, `destination_images`, `rag_places`, `itineraries`, `itinerary_days`, `itinerary_items`, `favorites`, `reviews`, `users`, and related legacy sources as before Phase 2B.
- **RAG runtime** — FastAPI RAG integration (URLs, headers, payloads for proxied paths) unchanged in contract; Node only relocated call sites into services where documented.
- **Transaction semantics** — Endpoints that were transactional remain transactional; endpoints that used sequential **`db.run`** without a transaction remain non-transactional (see below).

## 5. Important preserved transaction behavior

| Endpoint | Behavior |
|----------|----------|
| **`POST /itineraries/save-ai`** | Remains **transactional** via `itineraries.service.saveAiItinerary` (pool connection, begin/commit/rollback). |
| **`POST /ai/suggest-itinerary`** | Remains **transactional** for the persistence segment (itinerary + days + items in one transaction after model JSON is parsed). |
| **`POST /itineraries/create-from-option`** | Remains **non-transactional**: sequential **`db.run`** calls in service, same partial-write semantics as before extraction. |
| **`POST /itineraries/create-from-selection`** | Same as create-from-option: **non-transactional** sequential **`db.run`**. |

Intentionally **no** new global transactions were added for the create-from flows in Phase 2A, to avoid changing failure and rollback behavior without an explicit product decision.

## 6. Admin.js decision

`admin.js` was **audited** during the broader refactor timeline and **deferred**. Full refactor is postponed to a **later admin cleanup / security phase** because of mixed concerns (rendering, SQL, admin RAG proxy), size, and lower priority relative to Android runtime API stability.

## 7. Smoke test result

- Backend **starts successfully**.
- **`GET /health`** returns: `{"ok":true,"name":"smarttravel-backend"}`.

## 8. Recommended next phase

**Phase 2B — controlled v2 table switch planning and execution**

- Plan parity checks and rollout guardrails before moving read paths off legacy tables.
- **Start with the destinations read path only** (for example `destinations` / `destination_images` → `app_places` / `place_images`), keeping DTOs and response shapes stable.
- **Do not** switch AI, RAG, or create-from-option / create-from-selection resolution flows first; those depend on **`rag_places`** and related mapping, which should move later under a dedicated plan (for example `place_id_map`) with explicit persistence parity tests.

This ordering limits blast radius: place **listing/detail** reads migrate before **AI id resolution** and itinerary persistence mapping.
