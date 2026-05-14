# README_FIX_ALL.md

> Handoff document for **backend refactor of UnuTrip graduation project**.
> Audience: a fresh Cursor Agent that has **no prior chat context** and must implement
> the refactor in safe, behavior-preserving phases.
> Repository root: `E:\UNUtrip` (Windows / PowerShell, also runs on POSIX).

---

## 1. Goal

Professionalize the **Node.js backend** architecture so the codebase looks like a
thesis-grade, layered Express service — **without breaking any current behavior**.

Concretely:

- Introduce a clean `routes → controller → service → repository → db` layering.
- Centralize cross-cutting concerns (error handling, response envelope, request tracing, RAG client, DB transactions, uploads).
- Reduce route files that mix HTTP + SQL + business logic.
- Reduce duplicated logic (especially between `src/lib/ragUpstream.js` and the inline RAG helpers in `src/admin.js`).
- Improve test coverage.
- Keep the live system green at every step.

Non-goals (do **not** do, in any phase covered here):

- **Do not** change the Android-facing API contract (`/api/**`).
- **Do not** change the RAG upstream contract (`/health`, `/rag/chat`, `/rag/chat/simple`, `/ai/itinerary-preview`, `/ai/itinerary-options`, etc.).
- **Do not** modify the database schema.
- **Do not** touch `backend/rag/**` (FastAPI service) for the refactor.
- **Do not** edit any Android source (`app/`, `local.properties`, Gradle files).

---

## 2. Current architecture summary

### 2.1 Services & data flow

```
┌──────────┐        HTTPS         ┌─────────────────────┐        HTTP        ┌────────────────────┐
│ Android  │ ────────────────────▶│ backend/nodejs       │ ─────────────────▶ │ backend/rag        │
│ app/     │  Authorization: JWT  │ (Express, MySQL,     │  X-RAG-Internal-   │ (FastAPI, BM25,    │
│          │                       │  JWT, admin HTML)    │  Key, X-Request-ID │  Gemini, artifacts) │
└──────────┘                       └─────────────────────┘                    └────────────────────┘
                                            │                                        │
                                            ▼                                        ▼
                                    ┌───────────────┐                          ┌──────────────┐
                                    │ MySQL         │                          │ data/        │
                                    │ (unudata)     │                          │ artifacts/   │
                                    └───────────────┘                          └──────────────┘
```

- **`backend/nodejs`** is the only service Android talks to. It owns auth, persistence,
  uploads, the admin HTML dashboard, and the orchestration layer that forwards AI work to RAG.
- **`backend/rag`** owns the retrieval pipeline (BM25 + intent parser), the Gemini calls,
  rate limiting, and the AI itinerary preview/options. Node never calls Gemini directly.
- **Android → Node** uses standard JSON over HTTP, JWT auth, and multipart for uploads.
- **Node → RAG** uses internal HTTP with `X-RAG-Internal-Key` (set in `.env`) and
  propagates `X-Request-ID`.
- **Node → MySQL** uses `mysql2/promise` with a shared pool (`src/db.js`).

### 2.2 Main entry points

| Layer | File | Notes |
| --- | --- | --- |
| Node HTTP listener | `backend/nodejs/src/index.js` | Reads `BACKEND_PORT/HOST`, calls `assertSafeProductionConfig()`, then `createApp().listen(...)`. |
| Express factory | `backend/nodejs/src/app.js` | Mounts helmet/cors/morgan/json, static `/uploads`, `/images`, `/api`, `/admin`. Re-used by tests. |
| Public API router | `backend/nodejs/src/routes/index.js` | Calls `register*Routes(router)` for each feature. |
| Admin router | `backend/nodejs/src/admin.js` | Exports `buildAdminRouter()`. Server-rendered HTML + JSON. |
| RAG app | `backend/rag/app/main.py` | FastAPI app with routers + `/v1` mirror; loads RagPipeline + RagService at startup. |
| Legacy entry (unused) | `backend/nodejs/server.py` | Old Python local-LLM shim. Not used by current flow. |

### 2.3 Existing layer pattern (already partly clean)

```
HTTP routes (validation + envelope)
  └─ services (orchestration, DTO mapping, some transactions)
       └─ repositories (parameterized SQL only)
            └─ db.js (mysql2 pool + db.{query,get,run})
```

Features that already follow it well: **destinations**, **favorites**, **reviews**, **users** (mostly), **itineraries** (mostly), **health**.

### 2.4 What is good already

- Clear repository layer for v2 tables (`app_places`, `place_images`, `place_id_map`, etc.).
- Central RAG HTTP client with retries/timeouts in `src/lib/ragUpstream.js`.
- Central RAG response normalizer with zod in `src/schemas/ragContract.js`.
- Central env loading + production safety asserts in `src/config/env.js`.
- DTO mappers (`toUserDto`, `toDestinationDto`, `itineraryRowToDto`) in one place.
- `X-Request-ID` end-to-end (Node ↔ RAG) via `utils.resolveRequestTrace`.
- Reasonable JWT middleware (`src/auth.js`).
- Vitest + Supertest skeleton with mocked DB.

### 2.5 What is weak (driver for this refactor)

- `src/admin.js` is ~2200 lines and mixes HTML, SQL, RAG calls, validation, and password hashing.
- `src/routes/ai.routes.js → POST /api/ai/suggest-itinerary` opens a DB transaction with raw SQL **inside the route handler** (bypassing the service layer).
- `src/services/itineraries.service.js` has two near-duplicate flows (`createItineraryFromAiOption` / `createItineraryFromAiSelection`) that issue **non-transactional** `db.run` inserts.
- `src/routes/helpers.js` mixes DTO mappers, domain helpers (`resolveDestinationIdsFromSelection`, `flattenSelectedOptionDays`, `normalizeCategoryParam`), and repository calls.
- Error responses are built ad-hoc in each handler; there is no central Express error middleware.
- Response envelope drifts between endpoints (Android contract is fixed but inconsistent across endpoints).
- Two RAG HTTP clients exist (`src/lib/ragUpstream.js` and the inline helpers in `src/admin.js`).
- Test coverage is limited to 4 files (health, ai-rag-chat route, ragContract, ragUpstream).
- Inline `<script>` blocks in `src/admin.js` force `helmet` CSP to allow `'unsafe-inline'`.

---

## 3. Current backend folder map

> **All paths in this section are relative to `backend/nodejs/`** unless stated otherwise.

### Top-level

```
backend/nodejs/
├─ src/                  ← all server code
├─ tests/                ← Vitest tests (Node test env)
├─ public/images/        ← static assets served at /images
├─ uploads/              ← Multer destination served at /uploads
├─ docs/                 ← migration phase docs + Android contract checklist
├─ database.sql          ← snapshot of MySQL schema (read-only reference)
├─ server.py             ← legacy Python LLM shim, NOT wired in
├─ test_ai.js            ← ad-hoc local script
├─ package.json, package-lock.json
├─ eslint.config.js, .prettierrc.json, vitest.config.js
└─ README.md
```

### `src/` files (important ones)

| File | What it currently does | Safe to touch in Phase 1? | Risks if touched |
| --- | --- | --- | --- |
| `src/app.js` | Express app factory. Mounts `helmet`, `cors`, `express.json({ limit: "2mb" })`, `morgan("dev")`, static `/uploads`, `/images`, then `app.use("/api", buildRouter())` and `app.use("/admin", buildAdminRouter())`. | **Yes**, but only to add new middlewares (requestId early; notFound + errorHandler last). Do not change helmet/cors/json options. | Changing helmet CSP could break admin inline scripts; changing CORS could break Android in emulator (`10.0.2.2`). |
| `src/index.js` | Loads env, runs `assertSafeProductionConfig()`, calls `createApp().listen(PORT, HOST, ...)`. Logs serving paths. | **Optional** (only to add graceful shutdown). | Wrong shutdown order could leak DB pool. |
| `src/routes.js` | One-line re-export of `./routes/index.js`. | **Do not change**, just to be safe. | Some old import may rely on it. |
| `src/routes/index.js` | `buildRouter()` calls `register{Health,Auth,User,Favorite,Destination,Review,Itinerary,Ai}Routes(router)`. | **No, Phase 1 does not touch routes.** | Risk of breaking mount order. |
| `src/routes/health.routes.js` | `GET /health`, `GET /health/ready` (DB + optional RAG probe). | No (Phase 1). | None. |
| `src/routes/auth.routes.js` | `POST /auth/register|login|logout`, returns `{ success, message, token, user }`. | No (Phase 1). | Auth envelope is part of Android contract. |
| `src/routes/users.routes.js` | Profile / stats / preferences / avatar (multipart `avatar`). | No (Phase 1). | Multipart field name is part of contract. |
| `src/routes/favorites.routes.js` | List, add (404 if dest missing), delete. | No (Phase 1). | 404 mapping is part of contract. |
| `src/routes/destinations.routes.js` | List with paging+filters, featured, nearby (Haversine), detail. | No (Phase 1). | `distanceKm` and `isFavorite` are contract fields. |
| `src/routes/reviews.routes.js` | List by destination, create (multipart `images[0..2]`). | No (Phase 1). | Multipart field name and `images_json` aggregate are part of contract. |
| `src/routes/itineraries.routes.js` | List, detail (eager days+items), CRUD, items add, `save-ai`. Computes `totalDays` in the route (smell). | No (Phase 1). | Has bespoke error envelopes Android consumers may rely on. |
| `src/routes/ai.routes.js` | `/ai/suggest-itinerary` (inline transaction + raw SQL!), `/ai/rag-chat`, `/ai/chat`, `/ai/itinerary-preview`, `/ai/itinerary-options`, plus `/itineraries/create-from-option` and `/itineraries/create-from-selection`. | **No (Phase 1).** | Largest smell — defer to Phase 3. |
| `src/routes/helpers.js` | `toUserDto`, `toDestinationDto`, `itineraryRowToDto`, `attachDestinationImages`, `resolveDestinationIdsFromSelection`, `flattenSelectedOptionDays`, `normalizeCategoryParam`, `firstArrayValue`, `fixUrl`, `getUserById`. | **No (Phase 1).** Imported by services. | High blast radius. Move in Phase 2. |
| `src/routes/upload.js` | Multer factory for `avatars/` and `reviews/`. Not a route file. | No (Phase 1). | Filename pattern is observable by clients. |
| `src/services/destinations.service.js` | `listDestinationsPage`, `listFeaturedDestinationsForUser`, `listNearbyDestinationsForUser`, `getDestinationDetail`. | No (Phase 1). | Pulls from `routes/helpers.js` — moving requires Phase 2. |
| `src/services/favorites.service.js` | `listUserFavorites`, `addUserFavorite`, `removeUserFavorite`. | No (Phase 1). | Low risk, but defer. |
| `src/services/reviews.service.js` | `listReviewsForDestination`, `createReview` (also updates aggregate `rating/review_count`). | No (Phase 1). | Aggregate update is non-transactional — defer fix to Phase 3. |
| `src/services/itineraries.service.js` | List/detail/CRUD, `saveAiItinerary` (transactional!), `createItineraryFromAiOption` (NON-transactional, raw SQL), `createItineraryFromAiSelection` (NON-transactional, raw SQL). | **No (Phase 1).** | Highest-complexity file in services. Defer to Phase 3. |
| `src/services/ai.service.js` | `requestItineraryPreview`, `requestItineraryOptions`, `requestRagChatSimple`, `requestLocalAiChatAnswer`, `requestRagChatFallbackForAiChat`, `generateSuggestItineraryAiResult` (prompt + fallback + parse). | No (Phase 1). | Prompt + fallback order is tuned. |
| `src/repositories/users.repository.js` | All `users` table SQL incl. admin-update path. | No (Phase 1). | None as long as not edited. |
| `src/repositories/destinations.repository.js` | All `app_places` SELECTs (list/featured/nearby/by-id). | No (Phase 1). | None. |
| `src/repositories/destinationImages.repository.js` | `place_images` active rows by destination ids. | No (Phase 1). | None. |
| `src/repositories/favorites.repository.js` | Favorite list/add/remove + destination-exists check. | No (Phase 1). | None. |
| `src/repositories/reviews.repository.js` | Review list/insert + destination aggregate update. | No (Phase 1). | None. |
| `src/repositories/itineraries.repository.js` | Itinerary CRUD with optional `conn` for transactions. | No (Phase 1). | None. |
| `src/repositories/placeIdMap.repository.js` | `place_id_map` lookup (RAG `rawPlaceId` → `destinations.id`). | No (Phase 1). | Critical join key for AI flows. |
| `src/repositories/ai.repository.js` | `listDestinationsForAiSuggestion` used by `ai.service`. | No (Phase 1). | None. |
| `src/auth.js` | `signToken(payload)` + `authMiddleware(req,res,next)`. Default secret `smarttravel_dev_secret_change_me`. JWT expires `30d`. | **No (Phase 1).** | Token shape is part of Android contract. |
| `src/db.js` | `mysql2/promise` pool (limit 10, keep-alive) + `db.query`, `db.get`, `db.run` helpers. Has duplicate `dotenv.config(...)` call (harmless). Loads root `.env`. | **No (Phase 1)** for behavior. May be imported from `withTransaction.js` to expose `db.pool`. Do **not** rename `lastInsertRowid`. | Schema-coupled. |
| `src/utils.js` | `apiOk`, `apiFail`, `parseJsonArray`, `toIsoDate`, `daysBetweenInclusive`, `resolveRequestTrace`. | **Yes** — Phase 1 re-exports from `shared/http/response.js`. Preserve every existing export and signature. | Many files import from here. |
| `src/admin.js` | ~2200 lines. Dashboard, users CRUD, destinations CRUD, system, rag-ai dashboard, AI report. Inline HTML, inline SQL, custom RAG fetch helpers. | **No (Phase 1).** | Largest debt — Phase 4. |
| `src/lib/httpFetch.js` | `fetchWithTimeout(url, init, ms)`. | No (Phase 1). | None. |
| `src/lib/ragUpstream.js` | `ragPostJson(path, body, traceHeaders)` with retries on transient HTTP/network errors. | No (Phase 1). | Cross-service contract surface. |
| `src/config/env.js` | dotenv loader, JWT helpers, RAG URL, timeouts, prod safety, `getResolvedAiModelUrl`. | **No (Phase 1).** | Env contract. |
| `src/config/ragClient.js` | `ragUrl`, `ragAuthHeaders`, `ragAdminAuthHeaders`, `ragJsonHeaders`, `ragAdminJsonHeaders`. | No (Phase 1). | Header naming is locked. |
| `src/schemas/ragContract.js` | zod normalizer for `/rag/chat/simple` response. Lenient by design. | **No (Phase 1).** | Do not tighten. |
| `src/seed.js`, `src/data/destinations.json` | Legacy seeder (not wired in). | No (Phase 1). | Don't delete yet either. |
| `tests/` | `health.test.js`, `ai-rag-chat.route.test.js`, `ragContract.test.js`, `ragUpstream.test.js`. | **Yes** (only add `tests/setup/dbMock.js`; don't rewrite existing tests). | None. |

---

## 4. Android API contract freeze

> **All routes below are mounted under `/api`.** Do not move, rename, or change their request/response shape.

### 4.1 Endpoint inventory

| Method | Path | Auth | Owner file | Response shape risk |
| --- | --- | --- | --- | --- |
| GET | `/api/health` | Public | `health.routes.js` | `{ ok, service, uptime_s }` — locked. |
| GET | `/api/health/ready` | Public | `health.routes.js` | `{ ok, checks: { database, rag, error? } }` and 503 on failure. Locked. |
| POST | `/api/auth/register` | Public | `auth.routes.js` | `{ success, message, token, user }` — `data` is NOT used here. Locked. |
| POST | `/api/auth/login` | Public | `auth.routes.js` | Same envelope as register. Locked. |
| POST | `/api/auth/logout` | JWT | `auth.routes.js` | `apiOk(null, "Đã đăng xuất")` → `{ success:true, message:"Đã đăng xuất", data:null }`. |
| GET | `/api/users/profile` | JWT | `users.routes.js` | `apiOk(toUserDto)` — fields: `id, fullName, email, phone, avatar, preferences, createdAt`. |
| GET | `/api/users/stats` | JWT | `users.routes.js` | `apiOk({ itineraryCount, favoriteCount, reviewCount })`. |
| PUT | `/api/users/profile` | JWT | `users.routes.js` | Same as GET profile. |
| PUT | `/api/users/preferences` | JWT | `users.routes.js` | Same as GET profile. |
| POST | `/api/users/avatar` | JWT, multipart `avatar` | `users.routes.js` | Returns updated profile; avatar URL like `/uploads/avatars/<file>`. |
| GET | `/api/users/favorites` | JWT | `favorites.routes.js` | `{ success, data, total, page=1, limit=data.length }`. |
| POST | `/api/users/favorites` | JWT | `favorites.routes.js` | `apiOk(null, "OK")`; 404 if destination missing. |
| DELETE | `/api/users/favorites/:destinationId` | JWT | `favorites.routes.js` | `apiOk(null, "OK")`. |
| GET | `/api/destinations` | JWT | `destinations.routes.js` | `{ success, data, total, page, limit }`; `data[]` follows `toDestinationDto`. |
| GET | `/api/destinations/featured` | JWT | `destinations.routes.js` | Same envelope. |
| GET | `/api/destinations/nearby` | JWT | `destinations.routes.js` | Envelope **plus** `center: { lat, lng }, radiusKm`; items include `distanceKm`. |
| GET | `/api/destinations/:id` | JWT | `destinations.routes.js` | `{ success:true, data }` or `404 { success:false, message:"Not found", data:null }`. |
| GET | `/api/destinations/:id/reviews` | JWT | `reviews.routes.js` | `apiOk(rows)`; each item has `images` (array or null). |
| POST | `/api/reviews` | JWT, multipart `images` ×0..3 | `reviews.routes.js` | `apiOk(review)`. |
| GET | `/api/itineraries` | JWT | `itineraries.routes.js` | `{ success:true, data }`. |
| GET | `/api/itineraries/:id` | JWT | `itineraries.routes.js` | `apiOk({ ...itinerary, days: [...] })` with nested destinations as DTOs. |
| POST | `/api/itineraries` | JWT | `itineraries.routes.js` | `apiOk(itineraryDto)`. |
| POST | `/api/itineraries/:id/items` | JWT | `itineraries.routes.js` | `{ success:true, message:"Đã thêm vào lịch trình" }` with bespoke 4xx reasons (`missing_destination_id` → 400, `not_authorized` → 403, `no_days` → 400). |
| PUT | `/api/itineraries/:id` | JWT | `itineraries.routes.js` | `apiOk(itineraryDto)`. |
| DELETE | `/api/itineraries/:id` | JWT | `itineraries.routes.js` | `apiOk(null, "OK")`. |
| POST | `/api/itineraries/save-ai` | JWT | `itineraries.routes.js` | `{ success:true, message:"Đã lưu lịch trình thành công!" }`. |
| POST | `/api/ai/suggest-itinerary` | JWT | `ai.routes.js` | `{ success:true, itinerary:{...}, message }` or `500 { success:false, message }`. |
| POST | `/api/ai/rag-chat` | JWT | `ai.routes.js` | `{ success, message:"OK", answer, places, warnings, latency_ms, model_used, fallback_used, rag_mode, runtime_mode, raw }` or 502 envelope. |
| POST | `/api/ai/chat` | JWT | `ai.routes.js` | `{ success:true, answer }` or 502/500 with `message`. |
| POST | `/api/ai/itinerary-preview` | JWT | `ai.routes.js` | Pass-through of RAG response (no wrapping) or 502. |
| POST | `/api/ai/itinerary-options` | JWT | `ai.routes.js` | Pass-through of RAG response or 502. |
| POST | `/api/itineraries/create-from-option` | JWT | `ai.routes.js` | `{ success:true, message, data:{ id, itineraryId, optionId, selectedCount, unresolved } }` or 400 with `data.unresolved`. |
| POST | `/api/itineraries/create-from-selection` | JWT | `ai.routes.js` | `{ success:true, message, data:{ id, itineraryId, selectedCount, destinationIds, unresolved } }` or 400. |

### 4.2 Contract rules (do not violate)

1. **Paths are frozen.** Even though `create-from-option` / `create-from-selection` live in `ai.routes.js`, their public path is `/api/itineraries/*` — do not move them under `/api/ai/`.
2. **Request body field names are frozen** (`destinationIds`, `rawPlaceId`/`raw_place_id`/`placeId`/`place_id`, `selectedDestinations`, `selectedDestinationIds`, `dayNumber`, `startTime`, `endTime`, `note`, etc.).
3. **Response field names are frozen** (see `backend/nodejs/docs/API_COMPATIBILITY_CHECKLIST.md`).
4. **Status codes are frozen** (401 for missing/invalid JWT, 404 for missing destination/itinerary, 400 for bad payload, 502 for RAG upstream failure, 500 for server errors).
5. **Multipart field names are frozen** (`avatar`, `images`).
6. **Static URLs are frozen** — `/uploads/...` and `/images/...`. Android may join them with `API_BASE_URL`. Do not rename mounts.
7. **Auth header parsing is frozen** — `Authorization: Bearer <jwt>`, fallback to 401 with `{ success:false, message:"Unauthorized"|"Invalid token", data:null }`.
8. **JWT payload is frozen** — `{ userId, email }`, signed with `JWT_SECRET`, expiry `30d`.

---

## 5. RAG contract freeze

### 5.1 How Node calls RAG

- Base URL from `process.env.RAG_BASE_URL` (default `http://127.0.0.1:8001`).
- Constructed via `ragUrl(path)` in `src/config/ragClient.js`.
- Headers from `ragJsonHeaders()` / `ragAdminJsonHeaders()`. If `RAG_INTERNAL_API_KEY` (or `RAG_ADMIN_API_KEY` for `/admin/*`) is set, header `X-RAG-Internal-Key` is auto-attached.
- `X-Request-ID` is generated/preserved in `utils.resolveRequestTrace`, set on the Node response, and forwarded to RAG via `ragPostJson` (`src/lib/ragUpstream.js`).
- Retries: `RAG_FETCH_MAX_ATTEMPTS` (default 3) on transient HTTP (`429/502/503/504`) and transient network (`ECONNRESET/ETIMEDOUT/ECONNREFUSED`, `fetch failed`, etc.).
- Timeouts: `RAG_FETCH_TIMEOUT_MS` (default 90 000 ms), admin debug uses `RAG_ADMIN_DEBUG_TIMEOUT_MS` (default 120 000 ms).

### 5.2 Endpoints relied on

- `GET /health` — used by `/api/health/ready` (Node).
- `POST /rag/chat` — used by `ai.service.generateSuggestItineraryAiResult` fallback and admin AI report.
- `POST /rag/chat/simple` — used by `ai.service.requestRagChatSimple` and `requestRagChatFallbackForAiChat` (and tests).
- `POST /ai/itinerary-preview` — used by `ai.service.requestItineraryPreview`.
- `POST /ai/itinerary-options` — used by `ai.service.requestItineraryOptions`.
- Admin operations also call `/admin/system/overview`, `/admin/rag/status`, `/admin/system/self-test`, `/admin/ai/metrics`, `/admin/ai/logs`, `/admin/data-quality/status`, `/admin/data-quality/issues`, `/admin/rag/place-store/reload`, `/admin/cache/clear`, `/admin/ai/debug-query`. These are admin-only, but their request/response shape must remain stable.

### 5.3 Mapping bridge

- **`place_id_map` is the only join** between RAG’s `rawPlaceId` (string) and Node’s `destinations.id` (== `app_places.id` in v2).
- Always resolve via `placeIdMapRepository.getDestinationIdByRagPlaceId(rawPlaceId)`.
- Any code that drops or bypasses this lookup will produce `unresolved` items and break AI itinerary creation.

### 5.4 Schema rules

- `src/schemas/ragContract.js` uses `.passthrough()` and tolerates missing/extra fields. **Do not tighten validation in Phase 1.**
- Normalized defaults must remain (`answer: ""`, `places: []`, `warnings: []`, `model_used: "unknown"`, `fallback_used: false`, `rag_mode: "balanced"`, `runtime_mode: null`).

---

## 6. Database contract freeze

### 6.1 Tables Node reads/writes

| Table | Purpose |
| --- | --- |
| `users` | App users; password hash, preferences JSON, avatar. |
| `app_places` | Destination catalog (v2). Source of `category` ENUM, `rating`, `review_count`. |
| `place_images` | Destination images (active rows preferred over `images_json`). |
| `place_id_map` | RAG `rag_place_id` → `new_app_place_id`. |
| `favorites` | `(user_id, destination_id)` PK. |
| `reviews` | Per-destination user reviews; updates aggregate in `app_places`. |
| `itineraries` | Itinerary header. |
| `itinerary_days` | Day rows under an itinerary. |
| `itinerary_items` | Item rows (linked to `app_places.id`). |

A read-only reference snapshot of the schema is at `backend/nodejs/database.sql`.

### 6.2 `src/db.js` public API (do not change)

```js
import { db, pool, jsonOrNull, migrate } from "./db.js";

db.query(sql, params)   // returns rows array
db.get(sql, params)     // returns first row or undefined
db.run(sql, params)     // returns { lastInsertRowid, changes }
db.pool                  // raw mysql2/promise pool (for transactions)
pool                     // same as db.pool
jsonOrNull(value)        // tolerant JSON.parse
migrate()                // no-op in production-managed schema
```

Rules:

- **Do not** rename `lastInsertRowid` to `insertId` even though we are on MySQL — multiple repositories rely on the current naming.
- **Do not** change pool options (`connectionLimit: 10`, `enableKeepAlive: true`).
- **Do not** alter SQL or add new columns. Schema is frozen unless the user explicitly approves a change.
- It is acceptable for `withTransaction.js` to **import** `db` and use `db.pool.getConnection()`. No edit to `db.js` is required for that.

---

## 7. Main technical debt / risk files

### 7.1 `src/admin.js` (~2200 lines)

- **Why risky:** mixes server-rendered HTML (Tailwind via CDN + inline `<script>` blocks), inline SQL (16+ direct `db.{query,get,run}` calls), a private RAG client (`fetchRagJson`, `postRagJson`), password hashing, validation, and category normalization.
- **Phase 1 action:** **do not edit.** The shared plumbing introduced in Phase 1 must not affect admin output.
- **Future phase:** Phase 4 — split per-section files, extract HTML to `admin/views/*.html`, replace private RAG helpers with the shared `ragClient`, replace inline SQL with repositories, and add admin auth.

### 7.2 `src/routes/ai.routes.js`

- **Why risky:** `POST /api/ai/suggest-itinerary` runs a multi-statement DB transaction with raw SQL inside the route handler (bypassing service + repository). It also logs `req.body` (PII risk).
- **Phase 1 action:** **do not edit.**
- **Future phase:** Phase 3 — move the transaction into `ai.service.generateSuggestItineraryAiResult` or a dedicated service function using `withTransaction`. Remove `console.log` of raw bodies.

### 7.3 `src/routes/helpers.js`

- **Why risky:** confusingly named "routes helpers" but actually a **domain helper** module (DTO mappers, RAG `rawPlaceId` resolution, category normalization, user fetch via repository). It is imported by both routes **and** services. Moving it has high blast radius.
- **Phase 1 action:** **do not edit.**
- **Future phase:** Phase 2 — split into `modules/<feature>/dto.js` files + `shared/utils/*.js`. Convert the old file into a deprecated re-export shim until callers are migrated.

### 7.4 `src/services/itineraries.service.js`

- **Why risky:** holds two near-duplicate flows (`createItineraryFromAiOption`, `createItineraryFromAiSelection`) that perform multi-table inserts via **non-transactional** `db.run` calls. A failure mid-flight leaves partial itineraries in the DB.
- **Phase 1 action:** **do not edit.**
- **Future phase:** Phase 3 — wrap both with `withTransaction`, deduplicate scheduling logic, and reuse `itinerariesRepository.{insertItinerary,insertItineraryDay,insertItineraryItem}` with the `(payload, conn)` overload already supported.

### 7.5 Inconsistent error handling

- **Symptom:** each handler crafts its own `res.status(N).json({ success:false, message, data:null })`. There is no Express error middleware. Async throws may surface as unhandled rejections in some paths.
- **Phase 1 action:** add `errorHandler.middleware.js` and `asyncHandler.js` to the shared kit, but **do not change** existing handlers — they keep their own `try/catch`. The new error middleware will catch only what reaches `next(err)`, which today is "nothing".
- **Future phase:** Phase 2 progressively migrates each module to `next(new HttpError(...))`.

### 7.6 Inconsistent response envelope

- **Symptom:** auth returns `{ success, message, token, user }`; lists return `{ success, data, total, page, limit }`; some return `apiOk(...)`; AI proxies return raw RAG bodies; create-from-option returns `{ success, message, data }`. **This is part of the Android contract**, so it cannot be globally unified — only the implementation should be centralized later.
- **Phase 1 action:** **do not unify.** Provide `shared/http/response.js` as a tool, not as a forced policy.

### 7.7 Duplicated RAG client logic

- **Symptom:** `src/lib/ragUpstream.js` is the canonical client. `src/admin.js` reinvents `fetchRagJson` / `postRagJson` with its own error formatting and no retries.
- **Phase 1 action:** **do not consolidate yet.** Consolidation belongs to Phase 4 (admin cleanup).

### 7.8 Limited tests

- **Symptom:** only 4 test files; no coverage for auth, itinerary CRUD, favorites, destinations, reviews, admin.
- **Phase 1 action:** the only test-related change allowed is adding `tests/setup/dbMock.js` (optional helper). New test cases for endpoints land in Phase 5.

---

## 8. Target architecture (end state, not Phase 1)

```
backend/nodejs/src/
├── app.js                       ← Express factory (mounts middlewares + /api + /admin)
├── index.js  (or server.js)     ← HTTP listener + graceful shutdown
├── config/
│   ├── env.js
│   ├── rag.js                   ← was config/ragClient.js
│   └── logger.js
├── middlewares/
│   ├── auth.middleware.js
│   ├── requestId.middleware.js
│   ├── errorHandler.middleware.js
│   ├── notFound.middleware.js
│   └── validate.middleware.js
├── shared/
│   ├── http/
│   │   ├── HttpError.js
│   │   ├── asyncHandler.js
│   │   └── response.js
│   ├── db/
│   │   ├── pool.js              ← was db.js
│   │   └── withTransaction.js
│   ├── rag/
│   │   ├── ragClient.js
│   │   └── ragContract.js
│   ├── uploads/
│   │   └── multer.factory.js    ← was routes/upload.js
│   └── utils/
│       ├── date.js
│       ├── json.js
│       └── url.js
├── modules/
│   ├── auth/        (routes, controller, service, schema, dto)
│   ├── users/
│   ├── destinations/
│   ├── favorites/
│   ├── reviews/
│   ├── itineraries/
│   ├── ai/
│   └── health/
├── admin/
│   ├── admin.routes.js
│   ├── middleware/adminAuth.middleware.js
│   ├── users.admin.routes.js
│   ├── destinations.admin.routes.js
│   ├── system.admin.routes.js
│   ├── ragOps.admin.routes.js
│   ├── aiReport.admin.routes.js
│   └── views/
└── routes.js                    ← deprecated re-export shim (removed in Phase 4)
```

Per-feature flow:

```
HTTP request
  → routes file        (path + method only)
  → controller         (parse req, call service, map result to envelope)
  → service            (business logic, orchestration, transactions)
  → repository         (parameterized SQL only)
  → db.pool / mysql2
```

Phase 1 only seeds the **shared/** and **middlewares/** layers and wires `app.js`.
No module is moved, no feature behavior changes.

---

## 9. Full phase plan

### Phase 0 — Baseline (observe only)
1. Capture working state: `git status`, `npm test`, smoke each Android-critical endpoint.
2. Save sample response JSON for each endpoint listed in §4 to `backend/nodejs/docs/baseline_responses/` (manual or scripted).
3. **No code edits.**

### Phase 1 — Shared backend plumbing (the only phase implemented next)
- Add the shared kit (HTTP helpers, transaction helper, middlewares).
- Wire them into `app.js` (early requestId, late notFound + errorHandler).
- Keep `utils.js` 100% backward compatible.
- See §10 for the exact instructions a fresh Agent must follow.

### Phase 2 — Feature module migration (one feature per PR)
- Order: `health → auth → users → favorites → destinations → reviews → itineraries → ai`.
- Move each feature to `src/modules/<feature>/{routes,controller,service,repository,schema,dto}.js`.
- Replace `routes/helpers.js` callers with module-local DTOs + `shared/utils/*`.
- Convert handlers to `asyncHandler` + `next(new HttpError(...))` gradually.
- Re-export shims so Android keeps seeing the same endpoints.

### Phase 3 — AI / itinerary hardening
- Move the embedded transaction in `routes/ai.routes.js → /ai/suggest-itinerary` into the service via `withTransaction`.
- Wrap `createItineraryFromAiOption` / `createItineraryFromAiSelection` in `withTransaction`.
- Deduplicate scheduling logic (time slots, day distribution).
- Remove `console.log(req.body)` in `save-ai`.

### Phase 4 — Admin cleanup
- Split `src/admin.js` into `src/admin/*.admin.routes.js`.
- Extract HTML to `src/admin/views/*.html` (eliminates the inline `<script>` CSP exemption).
- Replace private RAG fetch helpers with the shared `ragClient`.
- Replace inline SQL in admin with repository calls.
- Add `adminAuth.middleware.js` (env-driven shared secret / basic-auth).

### Phase 5 — Tests, docs, docker
- Add unit + integration tests per module; contract tests vs. Phase 0 baseline snapshots.
- Add `pino`-based logger + structured request logging.
- Author `docs/ARCHITECTURE.md` (graduation-ready writeup).
- Add `docker-compose.yml` for `node + rag + mysql + redis` for the demo.

---

## 10. Phase 1 exact implementation guide

> **You are the next Agent.** Read **only** this document and the files listed in §10.1 below. Do not open or edit any file under §10.2.

### 10.1 Allowed files in Phase 1

Files to **create** (must not exist beforehand; if they already exist, stop and report):

1. `backend/nodejs/src/shared/http/HttpError.js`
2. `backend/nodejs/src/shared/http/asyncHandler.js`
3. `backend/nodejs/src/shared/http/response.js`
4. `backend/nodejs/src/shared/db/withTransaction.js`
5. `backend/nodejs/src/middlewares/requestId.middleware.js`
6. `backend/nodejs/src/middlewares/notFound.middleware.js`
7. `backend/nodejs/src/middlewares/errorHandler.middleware.js`

Files to **edit** (small, behavior-preserving edits only):

8. `backend/nodejs/src/app.js`
9. `backend/nodejs/src/utils.js`

Optional (touch **only** if extremely safe; skip on doubt):

10. `backend/nodejs/src/index.js` — only to add graceful shutdown (`SIGINT/SIGTERM → server.close() + pool.end()`).
11. `backend/nodejs/tests/setup/dbMock.js` — a centralized DB mock helper. Do **not** rewrite the existing tests; they keep their own mocks.

### 10.2 Forbidden files in Phase 1

Do **not** open, read for editing, or modify:

- All of `backend/nodejs/src/routes/*.routes.js` and `backend/nodejs/src/routes/index.js`, `backend/nodejs/src/routes.js`.
- `backend/nodejs/src/routes/helpers.js`
- `backend/nodejs/src/routes/upload.js`
- `backend/nodejs/src/services/*.service.js` (all of them, especially `ai.service.js` and `itineraries.service.js`)
- `backend/nodejs/src/repositories/*.repository.js`
- `backend/nodejs/src/admin.js`
- `backend/nodejs/src/schemas/ragContract.js`
- `backend/nodejs/src/lib/ragUpstream.js`, `backend/nodejs/src/lib/httpFetch.js`
- `backend/nodejs/src/config/env.js`, `backend/nodejs/src/config/ragClient.js`
- `backend/nodejs/src/auth.js`
- `backend/nodejs/src/db.js` — **may be imported** by `withTransaction.js`; **must not be edited**.
- `backend/nodejs/src/seed.js`, `backend/nodejs/src/data/destinations.json`
- `backend/nodejs/database.sql`
- `backend/nodejs/server.py`, `backend/nodejs/test_ai.js`
- `backend/nodejs/eslint.config.js`, `backend/nodejs/vitest.config.js`, `backend/nodejs/package.json`, `backend/nodejs/package-lock.json`, `.prettierrc.json`
- All existing tests under `backend/nodejs/tests/*.test.js`
- `backend/rag/**` (the entire RAG service)
- Android sources: `app/**`, `gradle*`, `local.properties`, root `build.gradle`, `settings.gradle`
- The repo-root `.env` and `.env.example`

### 10.3 New file specifications

#### 10.3.1 `backend/nodejs/src/shared/http/HttpError.js`

- **Purpose:** typed error class so handlers (now or in Phase 2) can throw and be caught by `errorHandler.middleware`.
- **Behavior:**
  - Class `HttpError` extends `Error`.
  - Constructor `(status, message, options = {})`.
  - Properties: `status: number`, `message: string`, `code?: string`, `details?: unknown`, `expose: boolean` (default `true` for `status < 500`).
  - Static helpers `HttpError.badRequest(msg, details?)`, `HttpError.unauthorized(msg = "Unauthorized")`, `HttpError.forbidden(msg = "Forbidden")`, `HttpError.notFound(msg = "Not found")`, `HttpError.conflict(msg)`, `HttpError.upstream(msg = "Upstream error", details?)` → 502, `HttpError.internal(msg = "Internal server error", details?)`.
- **Exports:** `export class HttpError ...`; named.
- **Constraints:** pure class, no imports from `src/**`. Do not mutate `Error.captureStackTrace` if not available (guard with `if (typeof Error.captureStackTrace === "function") ...`).

#### 10.3.2 `backend/nodejs/src/shared/http/asyncHandler.js`

- **Purpose:** wrap async route handlers so thrown errors reach Express `next(err)`.
- **Behavior:** export default and named `asyncHandler(fn) → (req, res, next) => Promise.resolve(fn(req, res, next)).catch(next)`.
- **Constraints:** zero side effects. Pure function. No imports.

#### 10.3.3 `backend/nodejs/src/shared/http/response.js`

- **Purpose:** canonical success envelope helpers. **Re-exported by `utils.js`** for backward compatibility.
- **Behavior:**
  - `export function apiOk(data, message = "OK")` → `{ success: true, message, data }`.
  - `export function apiFail(message = "Error", status = 400, data = null)` → `{ status, body: { success: false, message, data } }` (matches the current `utils.apiFail` signature exactly).
  - `export function apiList({ data, total, page = 1, limit = Array.isArray(data) ? data.length : 0 })` → `{ success: true, data, total, page, limit }` (new helper for future use; do **not** wire it into existing routes in Phase 1).
- **Constraints:** signatures of `apiOk` and `apiFail` must remain bit-identical to the current implementations in `src/utils.js` to avoid downstream breakage.

#### 10.3.4 `backend/nodejs/src/shared/db/withTransaction.js`

- **Purpose:** consistent BEGIN/COMMIT/ROLLBACK helper for the (future) services that need it.
- **Behavior:**
  - `import { db } from "../../db.js";` (this is the only allowed external import).
  - Export `async function withTransaction(work)` where `work` is `(conn) => Promise<T>`.
  - Implementation:
    ```js
    const conn = await db.pool.getConnection();
    try {
      await conn.beginTransaction();
      const result = await work(conn);
      await conn.commit();
      return result;
    } catch (err) {
      try { await conn.rollback(); } catch { /* ignore */ }
      throw err;
    } finally {
      conn.release();
    }
    ```
- **Constraints:**
  - Do **not** modify `src/db.js`.
  - Do **not** call this helper from any existing service in Phase 1. It just sits ready for Phase 3.

#### 10.3.5 `backend/nodejs/src/middlewares/requestId.middleware.js`

- **Purpose:** ensure every response carries `X-Request-ID` automatically (today only AI/RAG routes set it manually).
- **Behavior:**
  - `import { resolveRequestTrace } from "../utils.js";`
  - Export `requestIdMiddleware(req, res, next)`:
    ```js
    const { requestId, traceHeaders } = resolveRequestTrace(req.headers);
    req.requestId = requestId;
    req.traceHeaders = traceHeaders;          // available for downstream RAG calls
    res.setHeader("X-Request-ID", requestId);
    next();
    ```
- **Constraints:** must not overwrite an existing `X-Request-ID` header on the request (uses the existing utility which already handles incoming IDs).

#### 10.3.6 `backend/nodejs/src/middlewares/notFound.middleware.js`

- **Purpose:** handle unmatched routes consistently (today an unknown `/api/...` falls through Express defaults).
- **Behavior:**
  - `import { HttpError } from "../shared/http/HttpError.js";`
  - Export `notFoundMiddleware(req, res, next)` which `next(HttpError.notFound("Route not found"))`.
- **Constraints:**
  - Must be mounted **after** all routers (`/api`, `/admin`, static `/uploads`, `/images`).
  - Must **not** intercept paths handled by `express.static` — those already return their own 404. Express runs middlewares in order, so this is automatic as long as static mounts and routers run first.

#### 10.3.7 `backend/nodejs/src/middlewares/errorHandler.middleware.js`

- **Purpose:** central catch for any `next(err)` (currently almost never used by existing routes — that is intentional; this middleware is forward-looking and a safety net).
- **Behavior:**
  - `import { HttpError } from "../shared/http/HttpError.js";`
  - Export `errorHandlerMiddleware(err, req, res, next)`:
    1. If `res.headersSent`, delegate to `next(err)` so Express closes the connection. **Do not** try to write again.
    2. Compute `status = err instanceof HttpError ? err.status : 500`.
    3. Compute `message`:
       - If `err instanceof HttpError`: `err.message`.
       - Else if `process.env.NODE_ENV === "production"`: `"Internal server error"`.
       - Else: `err.message || String(err)`.
    4. Compute body:
       ```js
       const body = { success: false, message, data: null };
       if (err instanceof HttpError && err.details !== undefined) body.details = err.details;
       if (req.requestId) body.requestId = req.requestId;
       ```
       **Adding `data: null` and `requestId` is safe** because today no existing route reaches this middleware — they all handle their own responses. The new fields appear only on **new** error paths (and only if Phase 2+ routes funnel through here).
    5. In non-production, log via `console.error("[error]", { status, requestId: req.requestId, path: req.originalUrl, message: err.message, stack: err.stack });`. In production, omit `stack`.
    6. `res.status(status).json(body);`
- **Constraints:**
  - **Must not** change observable behavior of any **existing** endpoint. Verify by running the test suite and the manual checklist in §12.
  - **Must not** swallow `next(err)` after headers were sent.
  - Do not import any feature module. Only `HttpError`.

### 10.4 Edit specifications

#### 10.4.1 `backend/nodejs/src/app.js`

Add the following **without removing** anything currently mounted. Final order:

```js
import { createApp } from "./app.js"; // (for context; this is the existing factory)

// inside createApp() {
//   const app = express();
//   app.use(helmet({ ... }));            // unchanged
//   app.use(cors());                     // unchanged
//   app.use(express.json({ limit: "2mb" })); // unchanged
//   app.use(morgan("dev"));              // unchanged
//
//   // NEW: request id must be available to morgan-after handlers and downstream RAG calls
//   app.use(requestIdMiddleware);
//
//   app.use("/uploads", express.static(uploadsDir));    // unchanged
//   app.use("/images", express.static(publicImagesDir)); // unchanged
//   app.use("/api", buildRouter());                      // unchanged
//   app.use("/admin", buildAdminRouter());               // unchanged
//
//   // NEW: 404 + error handler last
//   app.use(notFoundMiddleware);
//   app.use(errorHandlerMiddleware);
//
//   return app;
// }
```

Required imports added to `app.js`:

```js
import { requestIdMiddleware } from "./middlewares/requestId.middleware.js";
import { notFoundMiddleware } from "./middlewares/notFound.middleware.js";
import { errorHandlerMiddleware } from "./middlewares/errorHandler.middleware.js";
```

Rules:

- **Do not** change the helmet, cors, or `express.json` options.
- **Do not** change the static mount paths.
- **Do not** change the order of helmet/cors/json/morgan.
- `requestIdMiddleware` goes after morgan (so logs already have basic context) but **before** routers (so handlers can use `req.requestId`).
- `notFoundMiddleware` and `errorHandlerMiddleware` go **last**, in that order.
- Run `node --check src/app.js` mentally — no other lines should move.

#### 10.4.2 `backend/nodejs/src/utils.js`

Goals:
- Keep every existing export (`apiOk`, `apiFail`, `parseJsonArray`, `toIsoDate`, `daysBetweenInclusive`, `resolveRequestTrace`).
- Re-export `apiOk` / `apiFail` from `shared/http/response.js` so the canonical source is the new file but every existing import (`from "../utils.js"`) still works.

Minimal pattern:

```js
// at top of utils.js
export { apiOk, apiFail } from "./shared/http/response.js";

// keep parseJsonArray, toIsoDate, daysBetweenInclusive, resolveRequestTrace as-is
```

Rules:

- Verify that `shared/http/response.js`'s `apiOk` / `apiFail` produce **identical objects** to the current implementations.
- Do **not** add new helpers to `utils.js`. New helpers (like `apiList`) live only in `shared/http/response.js`.
- Do **not** remove `resolveRequestTrace` from `utils.js`; the new middleware imports it from there.
- Do **not** change the signatures or default arguments.

### 10.5 Optional edits (skip on doubt)

#### 10.5.1 `backend/nodejs/src/index.js` (graceful shutdown)

If and only if it can be done without changing the listen behavior:

```js
const server = app.listen(PORT, HOST, () => { ... }); // capture server

function shutdown(signal) {
  console.log(`[server] received ${signal}, shutting down`);
  server.close(async () => {
    try { await (await import("./db.js")).pool.end(); } catch {}
    process.exit(0);
  });
  setTimeout(() => process.exit(1), 10_000).unref();
}
process.on("SIGINT", () => shutdown("SIGINT"));
process.on("SIGTERM", () => shutdown("SIGTERM"));
```

Rules:

- Must not change port/host resolution.
- Must not change the startup logs.
- Do **not** import `db` synchronously at top-level if it adds startup cost; the dynamic import above is fine.

#### 10.5.2 `backend/nodejs/tests/setup/dbMock.js` (optional helper)

- **Purpose:** centralize the `vi.mock("../src/db.js", ...)` pattern that today is repeated per file.
- **Behavior:** export `mockDb(initial = {})` which sets up `pool.query / db.query / db.get / db.run` mocks and returns mock fns.
- **Constraints:**
  - Do **not** modify any existing `*.test.js`.
  - Do **not** wire this into `vitest.config.js`.
  - It is an opt-in helper for Phase 2+ tests.

### 10.6 Constraints recap (do this exactly)

- **No** changes to routes, services, repositories, admin, RAG, config, env, db, schema.
- **No** package.json / lockfile / eslint / vitest config edits.
- **No** new dependencies (use built-ins: `node:crypto` for IDs is already available via `utils.resolveRequestTrace`).
- **No** behavior change for any currently-working endpoint.
- All new files must use **ESM** (`import` / `export`) consistent with the rest of `src/`.
- File contents must end with a single newline.
- Do not insert TODO/FIXME placeholders that the test suite would lint-fail on.

---

## 11. Phase 1 expected result

After Phase 1 is implemented:

- The new files in §10.3 exist and export the documented APIs.
- `src/app.js` mounts `requestIdMiddleware` early and `notFoundMiddleware` + `errorHandlerMiddleware` last; everything else in `app.js` is unchanged.
- `src/utils.js` re-exports `apiOk` and `apiFail` from `shared/http/response.js`; every existing import of `utils.js` still resolves to identical objects.
- Every existing Android-facing endpoint returns the same status, headers (with the addition of an automatic `X-Request-ID`), and body as before.
- Every existing RAG-facing call still resolves (same URL, same headers).
- DB schema is unchanged.
- `npm test` is green.
- `npm run lint` is green (no new ESLint errors).
- `npm run dev` starts the server with the same log lines (plus, optionally, a shutdown line when stopped).
- Phase 2 can begin by moving features one at a time into `src/modules/`.

---

## 12. Phase 1 test checklist

> Run from `backend/nodejs/` unless noted. Replace `<TOKEN>` with a JWT obtained via `POST /api/auth/login`.

### 12.1 Commands

```powershell
# 1. Repo status
cd E:\UNUtrip
git status

# 2. Install + test
cd .\backend\nodejs
npm install
npm test
npm run lint
npm run format:check    # optional

# 3. Boot server
npm run dev
# In a second terminal, run the manual endpoint checks below.

# 4. Stop with Ctrl+C and confirm graceful shutdown (only if optional step in §10.5.1 was implemented)
```

### 12.2 Manual endpoint checks

For each request, **confirm**:
- Same status code as before Phase 1.
- Same response body shape (envelope and field names).
- Response header `X-Request-ID` is present (new but harmless to Android).

```http
GET    /api/health                                  → 200 { ok:true, service:"smarttravel-backend", uptime_s:<number> }
GET    /api/health/ready                            → 200 (or 503 if DB/RAG down)
POST   /api/auth/login           { email, password } → 200 { success:true, message, token, user }
GET    /api/users/profile        Authorization: Bearer <TOKEN> → 200 apiOk(toUserDto)
GET    /api/destinations?page=1&limit=20            (with Bearer) → 200 { success, data:[...], total, page, limit }
GET    /api/destinations/featured                   (with Bearer) → 200 same envelope, length ≤ 5
GET    /api/users/favorites                         (with Bearer) → 200 { success, data:[...] }
POST   /api/users/favorites      { destinationId }  (with Bearer) → 200 apiOk(null,"OK") or 404 if missing
DELETE /api/users/favorites/:destinationId          (with Bearer) → 200 apiOk(null,"OK")
GET    /api/itineraries                             (with Bearer) → 200 { success:true, data:[...] }
POST   /api/ai/rag-chat          { message:"Gợi ý Nha Trang", top_k:6, mode:"balanced" } (with Bearer) → 200 envelope or 502
POST   /api/ai/chat              { message:"Hello" } (with Bearer) → 200 { success:true, answer:"..." } or 502
POST   /api/ai/suggest-itinerary { preferences:["beach"], startDate, endDate, budget? } (with Bearer)
   → 200 { success:true, itinerary, message } (transaction unchanged)
POST   /api/itineraries/create-from-option       (with Bearer)
   → 200 or 400 with `data.unresolved`
POST   /api/itineraries/create-from-selection    (with Bearer)
   → 200 or 400 with `data.unresolved`
GET    /admin/dashboard          (browser)           → renders HTML
```

### 12.3 Negative checks (still pass after Phase 1)

- Missing JWT → 401 `{ success:false, message:"Unauthorized", data:null }`.
- Invalid JSON body → 400 (existing behavior).
- Missing destination on add-favorite → 404 `{ success:false, message:"Destination not found", data:null }`.
- RAG service down → 502 `{ success:false, message:"FastAPI RAG trả lỗi" | "Không gọi được FastAPI RAG" }` (existing).
- Unknown route `GET /api/this-does-not-exist` → 404 with the new envelope `{ success:false, message:"Route not found", data:null, requestId:"..." }` — **this is the ONLY new visible behavior** Android could see. It is acceptable because Android never hits unknown paths in production.

### 12.4 Pass criteria

- All `npm test` cases pass.
- All endpoints above match their pre-Phase-1 responses (status + body shape).
- Server boots and shuts down cleanly.
- No new ESLint errors.
- No new dependency added in `package.json`.

If any of the above fails, **stop and report**. Do not proceed to Phase 2.

---

## 13. Agent handoff prompt for Phase 1

> Copy/paste this into a new Cursor Agent chat:

```
You are continuing the UnuTrip graduation-project backend refactor.

CONTEXT:
- The repository root is E:\UNUtrip.
- The Node backend lives in backend/nodejs/.
- There is a planning document at README_FIX_ALL.md in the repo root.
- An Android app consumes backend/nodejs over HTTP. backend/nodejs proxies AI work to backend/rag.
- The current system works and must not break.

TASK:
1. Read README_FIX_ALL.md fully. Treat it as the authoritative plan.
2. Implement Phase 1 exactly as described in section 10 of that README.
3. Touch ONLY the files listed in section 10.1 ("Allowed files in Phase 1").
4. Do NOT touch any file listed in section 10.2 ("Forbidden files in Phase 1"),
   including all routes, services, repositories, admin.js, schemas, lib, config,
   auth.js, db.js (read-only import is allowed), tests, package.json, backend/rag,
   and Android sources.
5. Preserve the Android API contract (section 4) and the RAG contract (section 5) byte-for-byte.
6. Do not modify the database schema.
7. After implementing, run the checklist in section 12 and report results.
8. If you encounter any ambiguity, stop and ask before writing code.

DELIVERABLES:
- 7 new files under backend/nodejs/src/shared/ and backend/nodejs/src/middlewares/.
- Minimal edits to backend/nodejs/src/app.js (wire 3 middlewares) and backend/nodejs/src/utils.js (re-export).
- Optional: graceful shutdown in backend/nodejs/src/index.js and tests/setup/dbMock.js.
- A short summary of changes + the test checklist result.

Start now by reading README_FIX_ALL.md only, then list the files you intend to create or edit, then proceed.
```

---

## 14. Phase 2 Result

> Implemented on the `v2/database-refactor` branch on top of the Phase 1 baseline
> commit `784f191`. This section is the running log of what actually shipped in
> Phase 2 and supersedes the high-level plan in §9 for that phase.

### 14.1 What was done

Phase 2 was executed as a **safe module shell migration**, not a deep business
refactor. For every feature listed in §9 the existing route file was split into
a thin route + controller pair under `src/modules/<feature>/`, while leaving
services, repositories, helpers, admin, db, lib, config, schemas, and tests
untouched.

- Routes files now only declare paths/methods and apply `authMiddleware` /
  `upload` middleware exactly where the old route did.
- Controllers contain the verbatim handler logic from the old route handlers
  (same validation, same try/catch, same response shapes, same error codes,
  same `console.log` lines, same Vietnamese strings).
- `src/routes/index.js` now imports the eight `register*Routes` functions
  from the new module paths.
- The old `src/routes/*.routes.js` files were converted into one-line
  compatibility re-export shims so any external import of those paths keeps
  working.
- No service, repository, helper, schema, lib, config, db, admin, RAG, Android,
  or schema file was modified. No new dependency was added.

### 14.2 Files created (16)

```
backend/nodejs/src/modules/
├── ai/
│   ├── ai.controller.js
│   └── ai.routes.js
├── auth/
│   ├── auth.controller.js
│   └── auth.routes.js
├── destinations/
│   ├── destinations.controller.js
│   └── destinations.routes.js
├── favorites/
│   ├── favorites.controller.js
│   └── favorites.routes.js
├── health/
│   ├── health.controller.js
│   └── health.routes.js
├── itineraries/
│   ├── itineraries.controller.js
│   └── itineraries.routes.js
├── reviews/
│   ├── reviews.controller.js
│   └── reviews.routes.js
└── users/
    ├── users.controller.js
    └── users.routes.js
```

### 14.3 Files modified (9 — all in `src/routes/`)

- `src/routes/index.js` — imports from `../modules/<feature>/<feature>.routes.js`.
- `src/routes/health.routes.js` — re-export shim.
- `src/routes/auth.routes.js` — re-export shim.
- `src/routes/users.routes.js` — re-export shim.
- `src/routes/favorites.routes.js` — re-export shim.
- `src/routes/destinations.routes.js` — re-export shim.
- `src/routes/reviews.routes.js` — re-export shim.
- `src/routes/itineraries.routes.js` — re-export shim.
- `src/routes/ai.routes.js` — re-export shim.

### 14.4 Files explicitly NOT modified

`backend/nodejs/src/services/**`, `backend/nodejs/src/repositories/**`,
`backend/nodejs/src/routes/helpers.js`, `backend/nodejs/src/routes/upload.js`,
`backend/nodejs/src/admin.js`, `backend/nodejs/src/db.js`,
`backend/nodejs/src/config/**`, `backend/nodejs/src/lib/**`,
`backend/nodejs/src/schemas/**`, `backend/nodejs/src/auth.js`,
`backend/nodejs/src/utils.js`, `backend/nodejs/src/app.js`,
`backend/nodejs/src/middlewares/**`, `backend/nodejs/src/shared/**`,
all existing tests, `package.json`, `package-lock.json`, `database.sql`,
`.env`, `.env.example`, `backend/rag/**`, and every Android source.

### 14.5 Verification

- **Endpoint paths unchanged.** Every path in the §4.1 inventory is still
  served, including the `/api/itineraries/create-from-option` and
  `/api/itineraries/create-from-selection` routes which remain registered by
  the ai module (their public path stays under `/api/itineraries/*`).
- **Response shapes unchanged.** Controllers reproduce the original response
  bodies field-for-field: `{ success, message, token, user }` for auth,
  `{ success, data, total, page, limit }` for paged lists, `apiOk(...)` for
  envelope endpoints, raw RAG pass-through for `/ai/itinerary-preview` and
  `/ai/itinerary-options`, and `{ success, message }` for ack endpoints.
  Vietnamese strings (`"Đăng nhập thành công"`, `"Đã thêm vào lịch trình"`,
  `"Không map được địa điểm nào sang destinations.id"`, etc.) preserved
  byte-for-byte.
- **Auth middleware placement unchanged.** Every route that previously took
  `authMiddleware` still does, in the same position relative to the multipart
  middleware where applicable.
- **Upload middleware placement unchanged.** `upload.single("avatar")` still
  wraps `POST /api/users/avatar`; `upload.array("images", 3)` still wraps
  `POST /api/reviews`. Field names (`avatar`, `images`) preserved.
- **SQL unchanged.** No service or repository SQL was touched. The raw-SQL
  transaction inside `/api/ai/suggest-itinerary` was moved verbatim into
  `ai.controller.js#suggestItinerary` (no logic change, no transactional
  upgrade — that remains Phase 3 work).
- **`createItineraryFromAiOption` / `createItineraryFromAiSelection`
  unchanged.** Both still call the existing non-transactional service
  functions; making them transactional is Phase 3.
- **DB schema unchanged.** `database.sql` not opened.
- **Android untouched.** No file under `app/` modified.
- **`backend/rag` untouched.** No FastAPI file modified.
- **`npm test` is green.** `4 test files passed, 7 tests passed` (same as
  Phase 1; no test regression). The `tests/ai-rag-chat.route.test.js` suite
  exercises the full app + module-routed handler and still returns the
  documented envelope.
- **App boots.** `createApp()` instantiates cleanly with all eight routers
  mounted through the new modules.

### 14.6 Special-case audits

- The embedded raw-SQL transaction in `POST /api/ai/suggest-itinerary` was
  **only relocated** from `src/routes/ai.routes.js` into
  `src/modules/ai/ai.controller.js#suggestItinerary`. SQL strings, parameter
  order, `'planned'` status literal, default times `"08:00"` / `"09:00"`,
  and the rollback/release sequence are identical. The `console.log("[AI]
  Save AI Itinerary Request:", ...)` in `saveAiItinerary` is also preserved
  for Phase 3 cleanup.
- The `routes/index.js` registration order is unchanged
  (health → auth → users → favorites → destinations → reviews → itineraries
  → ai), so Express still matches `/destinations/featured` and
  `/destinations/nearby` before the parameterized `/destinations/:id`.

### 14.7 What is NOT done in Phase 2 (deferred to Phase 3+)

- Wrapping `createItineraryFromAiOption` / `createItineraryFromAiSelection`
  in `withTransaction`.
- Moving the raw-SQL transaction in `suggestItinerary` into a service.
- Removing the `console.log(req.body)` in `save-ai`.
- Splitting `routes/helpers.js` into per-module DTO files.
- Splitting `admin.js`.
- Adding new test coverage per module.

These remain queued for Phases 3–5 per §9.

---

## 15. Phase 3 Result

> Implemented on the `v2/database-refactor` branch on top of the Phase 2
> commit `2057944`, against the plan in `README_FIX_ALL_PHASE3.md`. This
> section is the running log of what actually shipped in Phase 3 and
> supersedes the high-level plan in §9 for that phase.

### 15.1 What was done

Phase 3 was an **AI / itinerary transactional hardening** pass. Every change
preserves the Android API contract and the RAG contract byte-for-byte
(paths, status codes, response shapes, Vietnamese strings, default times,
default note strings). No schema, no repository, no route, no middleware,
no shared/http, no `withTransaction.js`, no test, and no `package.json`
was edited.

All four required work items (A, B, C, D) and both optional work items
(E, F) were implemented:

- **Work item A — `suggestItinerary` transaction relocated.** The ~60-line
  raw-SQL transaction inside `src/modules/ai/ai.controller.js#suggestItinerary`
  was replaced with a single call to a new service function
  `itinerariesService.persistAiSuggestedItinerary({ userId, aiResult,
  isoStart, isoEnd, totalDays, budget })`. The new function lives in
  `src/services/itineraries.service.js` (chosen over `ai.service.js` so it
  sits next to the other itinerary persistence flows and shares the
  `itinerariesRepository.insert*` overloads). It uses
  `withTransaction(async (conn) => …)` and the existing `(payload, conn)`
  repository overloads — `insertItinerary`, `insertItineraryDay`,
  `insertItineraryItem`. SQL strings, default values
  (`"Lịch trình AI tạo"`, `"Tạo bởi Hướng dẫn viên du lịch ảo."`, `'planned'`,
  `"08:00"` / `"09:00"`, `""`, `orderIdx` starting at `0`), and the
  `newItin` response object are byte-identical to the old controller
  block. The outer try/catch in the controller (and the
  `"Lỗi tạo lịch trình tự động: …"` 500 path, plus the
  `invalid_ai_json` → `"AI trả về dữ liệu không hợp lệ."` branch) are
  preserved. The now-unused `import { db }` line was removed from
  `ai.controller.js`.
- **Work item B — `createItineraryFromAiOption` made transactional.**
  All `db.run("INSERT INTO …")` calls in
  `src/services/itineraries.service.js#createItineraryFromAiOption` were
  replaced with `itinerariesRepository.insert*({…}, conn)` calls inside a
  single `withTransaction` boundary. Pre-flight validation
  (`flattenSelectedOptionDays`, `resolveDestinationIdsFromSelection`,
  `placeIdMapRepository.getDestinationIdByRagPlaceId` lookups, the
  `no_mapped_destinations` and `invalid_dates` early returns,
  `totalDays`, `finalBudget`, `destinationIdByRawPlaceId` map building,
  `timeSlots`) stays outside the transaction as required by §3.2.6 of the
  plan. The map-building loop was relocated above the `withTransaction(...)`
  call so all INSERTs are contiguous inside the boundary. `description ?? null`,
  `index + 1` for `orderIndex`, `item?.reason || "Được chọn từ AI tour"`,
  `timeSlots[index % timeSlots.length]`, and the
  `{ ok:true, data:{ id, itineraryId, optionId, selectedCount, unresolved } }`
  return shape are preserved bit-for-bit.
- **Work item C — `createItineraryFromAiSelection` made transactional.**
  Same pattern applied to `createItineraryFromAiSelection`. All raw
  `db.run` INSERTs replaced with repository overloads inside a single
  `withTransaction` boundary. `dayIds` array preserved in original order.
  The note string `"Được chọn từ AI gợi ý"` is intentionally different
  from the option flow's `"Được chọn từ AI tour"` and was kept exactly
  as before. The `dayIndex = i % totalDays` /
  `orderIndex = Math.floor(i / totalDays)` distribution math, the
  `slot = timeSlots[orderIndex % timeSlots.length]` rotation, and the
  `orderIndex + 1` value passed to the repository are all unchanged. The
  `{ ok:true, data:{ id, itineraryId, selectedCount, destinationIds, unresolved } }`
  return shape is preserved bit-for-bit.
- **Work item D — PII `console.log` dropped.** The
  `console.log("[AI] Save AI Itinerary Request:", JSON.stringify(req.body).substring(0, 500))`
  line at the top of
  `src/modules/itineraries/itineraries.controller.js#saveAiItinerary` was
  removed. The success ack (`"Đã lưu lịch trình thành công!"`), the 500
  failure shape (`"Lỗi lưu DB: " + detail`), and the operator-facing
  `console.error("Save AI Itinerary Error:", error)` log on failure were
  all kept exactly as before.
- **Work item E (optional) — `saveAiItinerary` service refactored.**
  The manual `db.pool.getConnection()` + `beginTransaction` / `commit` /
  `rollback` / `release` dance in
  `src/services/itineraries.service.js#saveAiItinerary` was replaced with
  a single `await withTransaction(async (conn) => { … })`. SQL,
  defaults (`"Lịch trình AI"`, `"Đã lưu từ gợi ý AI."`, `budget || null`,
  `"08:00"` / `"09:00"` / `""`, `orderIdx` starting at `0`), and the
  `safeStartDate` / `safeEndDate` / `totalDays` / `isoStart` / `isoEnd`
  derivation outside the transaction are unchanged. `db.pool.getConnection()`
  no longer appears anywhere outside `withTransaction.js`.
- **Work item F (optional) — shared `timeSlots` constant.** Created
  `backend/nodejs/src/shared/utils/timeSlots.js` exporting
  `DEFAULT_AI_ITINERARY_TIME_SLOTS` (the canonical
  `[["08:00","10:00"],["10:30","12:00"],["14:00","16:00"],["16:30","18:00"]]`
  array). Both `createItineraryFromAiOption` and
  `createItineraryFromAiSelection` now reference the imported constant
  via a `const timeSlots = DEFAULT_AI_ITINERARY_TIME_SLOTS` alias so the
  rotation expression `timeSlots[… % timeSlots.length]` continues to read
  identically. Values, order, count, and string formatting are
  byte-identical to the original local arrays. This is the only new file
  Phase 3 created.

The unused `import { db } from "../db.js"` at the top of
`src/services/itineraries.service.js` was removed (work items B, C, E
together eliminated the last reference to `db` in that module). The two
JSDoc comments that previously claimed the option/selection flows were
"non-transactional db.run" were updated to "wrapped in `withTransaction`
in Phase 3" so the documentation matches the implementation.

### 15.2 Files modified (3)

```
backend/nodejs/src/
├── modules/
│   ├── ai/
│   │   └── ai.controller.js                     ← work item A: trim suggestItinerary, drop `import { db }`
│   └── itineraries/
│       └── itineraries.controller.js            ← work item D: drop PII console.log line
└── services/
    └── itineraries.service.js                   ← work items B, C, E (+ A: persistAiSuggestedItinerary added at bottom)
                                                 ← work item F: import DEFAULT_AI_ITINERARY_TIME_SLOTS, alias both local timeSlots
                                                 ← drop now-unused `import { db }` and refresh two JSDoc lines
```

### 15.3 Files created (1)

```
backend/nodejs/src/shared/utils/timeSlots.js     ← work item F: DEFAULT_AI_ITINERARY_TIME_SLOTS constant
```

### 15.4 Files explicitly NOT modified

`backend/nodejs/src/modules/{auth,users,favorites,destinations,reviews,health}/**`,
`backend/nodejs/src/modules/ai/ai.routes.js`,
`backend/nodejs/src/modules/itineraries/itineraries.routes.js`,
`backend/nodejs/src/routes/**` (legacy shims and `routes/index.js`),
`backend/nodejs/src/repositories/**` (every `*.repository.js` is
unchanged — the `(payload, conn)` overloads were already in place from
Phase 1/2 and were used as-is),
`backend/nodejs/src/services/{ai,favorites,destinations,reviews}.service.js`
(no edits to any function in `ai.service.js`),
`backend/nodejs/src/admin.js`, `backend/nodejs/src/db.js`,
`backend/nodejs/src/auth.js`, `backend/nodejs/src/utils.js`,
`backend/nodejs/src/config/**`, `backend/nodejs/src/lib/**`,
`backend/nodejs/src/schemas/**`,
`backend/nodejs/src/shared/http/**`,
`backend/nodejs/src/shared/db/withTransaction.js` (imported, not edited),
`backend/nodejs/src/middlewares/**`, `backend/nodejs/src/app.js`,
`backend/nodejs/src/index.js`, `backend/nodejs/tests/**`,
`backend/nodejs/package.json`, `backend/nodejs/package-lock.json`,
`backend/nodejs/eslint.config.js`, `backend/nodejs/vitest.config.js`,
`backend/nodejs/.prettierrc.json`, `backend/nodejs/database.sql`,
`backend/nodejs/server.py`, `backend/nodejs/test_ai.js`,
`backend/nodejs/seed.js`, `.env`, `.env.example`,
`backend/rag/**`, and every Android source.

### 15.5 Verification

- **`npm test` is green.** `Test Files 4 passed (4)` / `Tests 7 passed (7)` —
  identical to the Phase 1/2 baseline. The `tests/ai-rag-chat.route.test.js`
  suite still exercises the full app boot through the module-routed
  handler and returns the documented envelope.
- **`npm run lint` is clean.** Zero ESLint findings across `src/` and
  `tests/`.
- **Endpoint shapes unchanged.** All four Phase-3-touched endpoints
  (`POST /api/ai/suggest-itinerary`, `POST /api/itineraries/save-ai`,
  `POST /api/itineraries/create-from-option`,
  `POST /api/itineraries/create-from-selection`) return the same
  HTTP statuses and the same JSON bodies as before — including the
  `no_mapped_destinations` and `invalid_dates` 400 paths and the
  `"AI trả về dữ liệu không hợp lệ."` / `"Lỗi tạo lịch trình tự động: …"`
  / `"Lỗi lưu DB: …"` failure envelopes.
- **Vietnamese strings byte-identical.** `"Lịch trình AI tạo"`,
  `"Tạo bởi Hướng dẫn viên du lịch ảo."`, `"Lịch trình AI"`,
  `"Đã lưu từ gợi ý AI."`, `"Được chọn từ AI tour"`,
  `"Được chọn từ AI gợi ý"`, `"Đã tạo lịch trình bằng AI thành công!"`,
  `"Đã lưu lịch trình thành công!"`,
  `"Tạo lịch trình từ tour AI thành công"`, and
  `"Tạo lịch trình từ AI gợi ý thành công"` are all preserved.
- **Repository public APIs unchanged.** No edit to any
  `*.repository.js`; only the existing `(payload, conn)` overloads on
  `insertItinerary` / `insertItineraryDay` / `insertItineraryItem` were
  consumed.
- **`db.pool.getConnection()` is now confined to
  `src/shared/db/withTransaction.js`.** The previously-direct call in
  `saveAiItinerary` is gone (work item E), as is the inline
  `conn = await db.pool.getConnection()` that Phase 2 had relocated into
  `ai.controller.js#suggestItinerary` (work item A).
- **`withTransaction` is used in exactly four service-layer call sites**
  (`createItineraryFromAiOption`, `createItineraryFromAiSelection`,
  `saveAiItinerary`, `persistAiSuggestedItinerary`) and zero controller
  call sites. The helper itself was not modified.
- **No new dependency.** `package.json` and `package-lock.json` are
  untouched.
- **PII `console.log` is gone** from `saveAiItinerary` (work item D).
  The operator-facing `console.error("Save AI Itinerary Error:", error)`
  on the failure path is intentionally retained.
- **DB schema unchanged.** `database.sql` not opened.
- **Android untouched.** No file under `app/` modified.
- **`backend/rag` untouched.** No FastAPI file modified.

### 15.6 What is NOT done in Phase 3 (deferred)

- Splitting `routes/helpers.js` into per-module DTO files (still
  shared between `services/itineraries.service.js` and the destinations
  module).
- Splitting `admin.js`.
- Adding new test coverage per module.
- Anything under `backend/rag/**` or any Android source.

These remain queued for Phases 4–5 per §9.

---

*End of `README_FIX_ALL.md`. This document is the single source of truth for the upcoming refactor phases. Update it at the end of each phase to reflect new realities.*
