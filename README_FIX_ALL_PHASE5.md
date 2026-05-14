# README_FIX_ALL_PHASE5.md

> Handoff document for **Phase 5 of the UnuTrip backend refactor**.
> Audience: a fresh Cursor Agent that has **no prior chat context** and must
> implement Phase 5 in safe, behavior-preserving steps.
> Repository root: `E:\UNUtrip` (Windows / PowerShell, also runs on POSIX).
> This document is the **single source of truth** for Phase 5. The parent
> document `README_FIX_ALL.md` is informational context only; you do **not**
> need to open it to do Phase 5 — everything you need is here.

---

## 1. Mission

**Phase 5 = DTO split + first test coverage for Phase 1–4 additions +
optional admin SQL repository sweep.**

After Phase 4 shipped (admin module shell + HTTP Basic Auth gate), three
cross-cutting messes remain in the Node backend:

1. **`src/routes/helpers.js` is a 263-line grab-bag** that mixes three
   unrelated DTO concerns (user DTO, destination DTO, itinerary DTO)
   plus the `normalizeCategoryParam` enum normalizer plus the
   `firstArrayValue` utility. It's imported by 8 different files across
   `modules/`, `services/`, and itself depends on three different
   repositories. The Phase 2 work item §14.7 explicitly flagged it as
   "deferred to Phases 3–5".
2. **Phase 4 added the `adminAuth` middleware but no tests cover it.**
   `npm test` is still the same `4 passed (4) / 7 passed (7)` baseline
   from Phase 1. The auth matrix (dev-mode passthrough, missing /
   malformed / wrong-scheme / wrong-creds → 401, correct creds → 200,
   one-time warning guard) is exercised only by manual smoke tests
   from the Phase 4 chat — that's a regression risk going forward.
3. **The remaining inline admin SQL** that Phase 4 left in place — the
   user listing query with `?q=` search, the destination listing query
   with `?q=` search, `POST /destinations/save` (the UPDATE branch plus
   the next-id-lookup + INSERT branch), and the
   `GET /ai-report` category aggregate + rating average — still lives
   inside the route handlers in `src/admin/{users,destinations,aiReport}.admin.routes.js`.
   Phase 4 piloted only the simplest two queries per file; the rest
   was intentionally deferred.

Phase 5 cleans up the **shape** of those three items without touching
their **behavior**:

1. **Split `routes/helpers.js`** into three per-domain DTO modules
   (`src/shared/dto/userDto.js`, `destinationDto.js`, `itineraryDto.js`)
   and reduce `routes/helpers.js` to a one-line re-export shim. Every
   function signature and every function body is preserved bit-for-bit
   — only the file each function lives in changes. Eight existing
   import sites continue to work unchanged through the shim.
2. **Add new vitest test coverage** for the `adminAuth` middleware
   (`tests/adminAuth.middleware.test.js`) and for the admin router
   registration shape (`tests/admin.router.test.js`). No existing test
   file is modified.
3. **(Optional, only if 1–2 land green)** Continue the Phase 4 admin
   SQL extraction pilot for the remaining inline `db.*` calls in
   `users.admin.routes.js`, `destinations.admin.routes.js`, and
   `aiReport.admin.routes.js`. New repository functions are **added**
   to the existing `users.repository.js` and
   `destinations.repository.js`; no existing function is modified. The
   `GET /ai-report` aggregates land on a small new
   `repositories/appPlacesStats.repository.js` (single-purpose file)
   because the existing `destinations.repository.js` does not own
   aggregate queries.

**Goal:** preserve every byte of the rendered HTML, the JSON responses,
the redirect URLs, the form field names, the Vietnamese strings, the
Android API contract, and the RAG admin contract. After Phase 5, every
URL under `/api/**` and `/admin/**` returns the same status code, the
same headers, and the same body as before.

**Non-goals (forbidden in Phase 5):**

- **Do not** change any rendered HTML byte-for-byte. The admin
  templates stay frozen exactly as Phase 4 left them.
- **Do not** change any `/admin/*` or `/api/**` URL path, request
  body field name, redirect target, form field name, or HTTP status
  code.
- **Do not** extract HTML to external `.html` template files — that
  is Phase 6 work. Templates remain inline in JS template literals.
- **Do not** tighten the helmet CSP. Phase 6 owns the
  `'unsafe-inline'` / `scriptSrcAttr` removal alongside the template
  extraction.
- **Do not** modify the Android-facing API contract under `/api/**`.
- **Do not** modify the RAG upstream contract.
- **Do not** modify the database schema.
- **Do not** touch `backend/rag/**` (FastAPI service).
- **Do not** touch any Android source (`app/**`, Gradle files, etc.).
- **Do not** add new dependencies.
- **Do not** modify any existing repository function body or signature.
  Work item C adds new functions only.
- **Do not** rewrite any handler body in `src/modules/**` or
  `src/admin/**`. Imports may change to follow the helpers.js split
  through the shim. Inline `db.*` calls in admin (work item C) may be
  replaced with repository calls, but the rest of the handler body
  (validation, error envelopes, Vietnamese strings) stays byte-identical.
- **Do not** edit `package.json`, `package-lock.json`, `database.sql`,
  `eslint.config.js`, `vitest.config.js`, any `.prettierrc.json`, or
  any file under `src/config/`, `src/lib/`, `src/schemas/`,
  `src/middlewares/`, or `src/shared/{http,db,utils}/**`. The DTO
  split lands a new `src/shared/dto/` subdirectory — that path
  is allowed because it's brand new.
- **Do not** edit `.env` or `.env.example`. The two ADMIN_BASIC_*
  documentation lines from Phase 4 are unchanged.

---

## 2. Current state (after Phases 1 + 2 + 3 + 4, all committed)

Five prior commits land before Phase 5:

| Commit | What it did |
| --- | --- |
| `c8bade9` — **Phase 1** | Shared plumbing: `HttpError`, `asyncHandler`, response helpers, `withTransaction`, `requestId` / `notFound` / `errorHandler` middlewares. |
| `2057944` — **Phase 2** | Module shell migration — all 8 `/api/**` feature routes moved into `src/modules/<feature>/{routes,controller}.js`; old `routes/*.routes.js` reduced to re-export shims. |
| `7f04026` — **Phase 3** | AI / itinerary transactional hardening (`withTransaction` + `persistAiSuggestedItinerary` + PII `console.log` drop + `DEFAULT_AI_ITINERARY_TIME_SLOTS`). |
| `974fd9f` — **Phase 4** | Admin module shell migration: 1997-line `admin.js` split into 11 files under `src/admin/`; new `adminAuth.middleware.js` with default-open HTTP Basic Auth; two pilot repository extractions in `users.repository.js` and `destinations.repository.js`. |
| (older docs) | `cf47f11` — Phase 4 plan; `fd4f15d` — Phase 3 plan. |

You should start Phase 5 with a **clean working tree** on branch
`v2/database-refactor`. Verify with `git status` before starting.

### Layer map (as of start of Phase 5)

```
backend/nodejs/src/
├── app.js                              Express factory (mounts /api and /admin; /admin uses adminAuthMiddleware)
├── index.js                            HTTP listener
├── routes.js                           one-line re-export of ./routes/index.js (legacy)
├── routes/
│   ├── index.js                        registerApiRoutes(router) — calls every register*Routes()
│   ├── *.routes.js                     Phase 2 re-export shims pointing at modules/<feature>/
│   └── helpers.js                      ← Phase 5 must split this file (263 lines, 10 exports)
├── modules/                            Phase 2 controllers/routes (FROZEN in Phase 5)
├── services/                           Phase 3 transactional services (FROZEN in Phase 5)
├── repositories/                       Phase 4 added 4 new admin-pilot fns (rest FROZEN in Phase 5)
├── admin.js                            6-line re-export shim from Phase 4 (FROZEN in Phase 5)
├── admin/                              Phase 4 split — 11 files (FROZEN in Phase 5 except work item C)
├── middlewares/                        Phase 1 + Phase 4 (adminAuth) — FROZEN in Phase 5
├── shared/
│   ├── http/                           HttpError, response helpers (FROZEN)
│   ├── db/                             withTransaction (FROZEN)
│   ├── utils/timeSlots.js              Phase 3 (FROZEN)
│   └── dto/                            ← Phase 5 creates this directory
├── config/, lib/, schemas/, auth.js, db.js, utils.js   ALL FROZEN
└── seed.js, data/                      FROZEN

backend/nodejs/tests/
├── ragContract.test.js                 FROZEN
├── ragUpstream.test.js                 FROZEN
├── health.test.js                      FROZEN
├── ai-rag-chat.route.test.js           FROZEN
├── adminAuth.middleware.test.js        ← Phase 5 creates this file
└── admin.router.test.js                ← Phase 5 creates this file (optional)
```

After Phase 5 the routes/helpers.js layout becomes:

```
backend/nodejs/src/
├── shared/dto/
│   ├── userDto.js                      toUserDto, getUserById, firstArrayValue
│   ├── destinationDto.js               toDestinationDto, attachDestinationImages, fixUrl, normalizeCategoryParam
│   └── itineraryDto.js                 itineraryRowToDto, flattenSelectedOptionDays, resolveDestinationIdsFromSelection
└── routes/
    └── helpers.js                      one-line re-export shim (mirrors Phase 2 / Phase 4 pattern)
```

---

## 3. What Phase 5 must do — the work items

### 3.1 Work item A (REQUIRED) — split `routes/helpers.js` into per-domain DTO modules

**Symptom.** `src/routes/helpers.js` (263 lines) currently exports **10
names** that span three unrelated domains plus a couple of generics:

| Export | Domain | Current consumers |
| --- | --- | --- |
| `toUserDto` | user | `modules/auth/auth.controller.js`, `modules/users/users.controller.js` |
| `getUserById` | user | `modules/users/users.controller.js`, `services/reviews.service.js` |
| `firstArrayValue` | user (only consumer is users controller) | `modules/users/users.controller.js` |
| `toDestinationDto` | destination | `services/destinations.service.js`, `services/favorites.service.js`, `services/itineraries.service.js` |
| `attachDestinationImages` | destination | `services/destinations.service.js`, `services/favorites.service.js`, `services/itineraries.service.js` |
| `fixUrl` | destination (used internally + by other DTOs) | (also internal to `getDestinationImages` inside `helpers.js`) |
| `normalizeCategoryParam` | destination | `modules/destinations/destinations.controller.js` |
| `itineraryRowToDto` | itinerary | `services/itineraries.service.js` |
| `flattenSelectedOptionDays` | itinerary | `services/itineraries.service.js` |
| `resolveDestinationIdsFromSelection` | itinerary | `services/itineraries.service.js` |

It's also internally tangled: `toUserDto` and `toDestinationDto` both
call `fixUrl`; `getDestinationImages` (private, used by
`toDestinationDto`) calls `fixUrl`. The split must preserve all of
these internal calls.

**Required Phase-5 change.**

1. Create `backend/nodejs/src/shared/dto/userDto.js`:
   ```js
   import { parseJsonArray } from "../../utils.js";
   import * as usersRepository from "../../repositories/users.repository.js";

   // fixUrl is imported from the destination DTO module because it is
   // shared between the two DTOs.
   import { fixUrl } from "./destinationDto.js";

   export function toUserDto(row) { /* byte-identical body */ }
   export async function getUserById(id) { /* byte-identical body */ }
   export function firstArrayValue(obj) { /* byte-identical body */ }
   ```
   Move all three exports verbatim. `getUserById` still throws
   `new Error("User not found")` when the lookup fails; do **not**
   convert it to `HttpError`.

2. Create `backend/nodejs/src/shared/dto/destinationDto.js`:
   ```js
   import { parseJsonArray } from "../../utils.js";
   import * as destinationImagesRepository from "../../repositories/destinationImages.repository.js";

   function getImageUrlValue(value) { /* byte-identical body */ }
   export function fixUrl(value) { /* byte-identical body */ }
   function getDestinationImages(row) { /* byte-identical body */ }

   export async function attachDestinationImages(rows) { /* byte-identical body */ }
   export function normalizeCategoryParam(value) { /* byte-identical body */ }
   export function toDestinationDto(row, isFavorite) { /* byte-identical body */ }
   ```
   `getImageUrlValue` and `getDestinationImages` are **private** to the
   destination DTO. They stay non-exported. `fixUrl` is exported because
   the user DTO needs it for the `avatar` field (it currently lives in
   the same file, so the same-file call works today; after the split,
   `userDto.js` imports it).

3. Create `backend/nodejs/src/shared/dto/itineraryDto.js`:
   ```js
   import * as placeIdMapRepository from "../../repositories/placeIdMap.repository.js";

   export function flattenSelectedOptionDays(days) { /* byte-identical body */ }
   export async function resolveDestinationIdsFromSelection(selectedDestinations) { /* byte-identical body */ }
   export function itineraryRowToDto(row, days) { /* byte-identical body */ }
   ```
   Three exports, byte-identical bodies. Note: the
   `placeIdMapRepository.getDestinationIdByRagPlaceId(rawPlaceId)` call
   inside `resolveDestinationIdsFromSelection` is the only repository
   touchpoint, and its import path changes from `../repositories/…` to
   `../../repositories/…` because the new file is one directory deeper.

4. Replace `backend/nodejs/src/routes/helpers.js` with a re-export shim
   that pulls every existing export from the three new modules so
   existing import sites continue to work unchanged:
   ```js
   /**
    * Phase 5 compatibility shim — implementation moved to
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
   ```

   The eight existing import sites in `modules/auth/auth.controller.js`,
   `modules/users/users.controller.js`,
   `modules/destinations/destinations.controller.js`,
   `services/destinations.service.js`,
   `services/favorites.service.js`,
   `services/itineraries.service.js`, and `services/reviews.service.js`
   continue to work through the shim. **Do not** edit those import
   sites in Phase 5 — that's a low-value churn that risks introducing
   bugs and pollutes the diff. The shim exists precisely so callers
   don't have to change.

**Forbidden in work item A.**

- Do not change any function body byte-for-byte.
- Do not change export names. Three modules each export exactly the
  names listed in §3.1.1 / §3.1.2 / §3.1.3.
- Do not export `getImageUrlValue` or `getDestinationImages`. They were
  private inside `helpers.js`; they must stay private inside
  `destinationDto.js`.
- Do not introduce circular imports. The dependency direction is
  `userDto.js` → `destinationDto.js` (only the `fixUrl` call). Do not
  add a reverse import from `destinationDto.js` back to `userDto.js`.
- Do not edit `src/utils.js` (the `parseJsonArray` source). Both new
  DTO modules import it as-is.
- Do not edit any of the 8 consumer files in this work item.

---

### 3.2 Work item B (REQUIRED) — add `tests/adminAuth.middleware.test.js`

**Symptom.** Phase 4 added `adminAuth.middleware.js` with a non-trivial
behavior matrix (dev-mode passthrough + one-time warning, gated mode +
six different 401 trigger conditions, gated mode + 200 on correct
creds). The matrix was smoke-tested manually in the Phase 4 chat but
no automated test exercises it, so a future edit could silently break
the contract without `npm test` catching it.

**Required Phase-5 change.**

1. Create `backend/nodejs/tests/adminAuth.middleware.test.js`. Use
   vitest + supertest in the same style as the existing
   `tests/health.test.js`. Build a one-route Express app per test
   (mount `adminAuthMiddleware` on a single GET handler that returns
   `200 "OK"`) so the test does not touch the real `createApp()`
   factory, the DB, the RAG client, or any other middleware.

2. Use vitest's `beforeEach` / `afterEach` to save and restore
   `process.env.ADMIN_BASIC_USER` and `process.env.ADMIN_BASIC_PASS`
   and the `console.warn` spy so individual tests don't leak state.

3. Cover at minimum these cases (each is one `it(…)`):
   - **Dev-mode passthrough** — both env vars unset: request returns
     `200 "OK"` and `console.warn` is called exactly once with a
     message matching `/ADMIN_BASIC_USER\/ADMIN_BASIC_PASS not set/`.
   - **Dev-mode warning is one-time across multiple requests** —
     issue two requests; the spy is still called exactly once.
   - **Gated mode, no Authorization header** — both env vars set,
     no header: response is `401`, body equals `"Unauthorized"`,
     `WWW-Authenticate` header equals
     `Basic realm="UnuTrip Admin"`.
   - **Gated mode, wrong scheme** — `Authorization: Bearer abc`:
     same `401` envelope as above.
   - **Gated mode, malformed Basic value (missing colon)** —
     `Authorization: Basic ` + `Buffer.from("admin", "utf8").toString("base64")`:
     same `401` envelope.
   - **Gated mode, wrong password** — credentials `admin:wrong`
     base64-encoded: same `401` envelope.
   - **Gated mode, wrong username** — credentials `wrong:secret`:
     same `401` envelope.
   - **Gated mode, correct credentials** — `admin:secret`: response
     is `200`, body equals `"OK"`, no `WWW-Authenticate` header set.
   - **Gated mode, credentials with a colon in the password** —
     credentials `admin:s:e:c` (split at first colon): config sets
     `ADMIN_BASIC_PASS=s:e:c`; response is `200 "OK"`. This guards the
     `decoded.indexOf(":")` split that uses the **first** colon.

4. Important — the `warned` module-level guard inside
   `adminAuth.middleware.js` is set once per process lifetime. Vitest
   isolates each test file in a worker, but **within a single test
   file**, multiple `it(…)` cases share the same import. Use
   `vi.resetModules()` plus a dynamic `await import(...)` at the top of
   each `describe`/`it` that needs a fresh `warned = false` state.
   Document this in a comment on the test file so future readers know
   why the dynamic import is there.

**Forbidden in work item B.**

- Do not modify `adminAuth.middleware.js`. The middleware is frozen in
  Phase 5; the test must adapt to the existing behavior.
- Do not modify any other middleware. Do not import `createApp()` —
  building a per-test Express app keeps the suite hermetic and fast.
- Do not add a network call or a DB call. The auth middleware does
  neither; the test must not either.
- Do not change `vitest.config.js`. The new test file is auto-picked
  up by the default `tests/**/*.test.js` glob.
- Do not add any new npm dependency. `supertest` is already a dev
  dependency (used by `health.test.js` and `ai-rag-chat.route.test.js`).

---

### 3.3 Work item C (OPTIONAL — only if A and B are green) — continue the admin SQL repository sweep

**Symptom.** Phase 4 piloted only the simplest two queries per file
(the single-row `GET /…/api/:id` lookup and the
`POST /…/delete/:id`). The other inline `db.*` calls in the admin
section files are still there:

- `src/admin/users.admin.routes.js`
  - The conditional listing query: with-`?q=` search variant (4-column
    LIKE) and the no-search variant (`ORDER BY created_at DESC`).
  - The `POST /users/save` flow's `bcrypt.hashSync` + `db.run` UPDATE
    /INSERT — this stays inline (work items C does NOT touch save; see
    forbidden list).
- `src/admin/destinations.admin.routes.js`
  - The conditional listing query: with-`?q=` search variant (6-column
    LIKE on `name`, `city`, `province`, `address`, `category`, `id`) and
    the no-search variant.
  - The `POST /destinations/save` flow's UPDATE branch.
  - The `POST /destinations/save` flow's
    `SELECT COALESCE(MAX(id), 0) + 1 …` next-id pick + INSERT branch.
- `src/admin/aiReport.admin.routes.js`
  - The category aggregate:
    `SELECT category, COUNT(*) as count FROM app_places GROUP BY category`.
  - The rating average: `SELECT AVG(rating) as avgRating FROM app_places`.

**Required Phase-5 change (only if you do work item C).**

1. Add new exported functions to
   `backend/nodejs/src/repositories/users.repository.js`. Pick names
   in the convention already used in Phase 4
   (`getAdminUserDetailById`, `deleteUserById`). For example:
   - `listAdminUsers()` — `SELECT id, full_name, email, phone, created_at FROM users ORDER BY created_at DESC` (exact SQL).
   - `searchAdminUsers({ like })` — the 4-column LIKE query with
     `[like, like, like, like]` parameter shape.

2. Add new exported functions to
   `backend/nodejs/src/repositories/destinations.repository.js`:
   - `listAdminDestinations()` — `SELECT id, name, city, province, category, rating FROM app_places ORDER BY id DESC` (exact SQL).
   - `searchAdminDestinations({ like })` — the 6-column LIKE query
     with `[like, like, like, like, like, like]` parameter shape.
   - `updateAdminDestination({ id, name, description, address, city, province, latitude, longitude, category, openTime, closeTime })`
     — exact same UPDATE statement as the inline one in
     `POST /destinations/save`. Parameter order and `?` placeholder
     count must match.
   - `getNextAppPlaceId()` — `SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM app_places` returning the raw row (the admin handler reads `nextRow?.next_id`).
   - `insertAdminDestination({ id, placeKey, name, description, shortDescription, address, city, province, latitude, longitude, category, openTime, closeTime })`
     — exact same INSERT statement as the inline one (with the
     `tags_json='[]'`, `kid_friendly=0`, `elderly_friendly=0`,
     `is_active=1`, `rating=0`, `review_count=0` defaults baked into
     the SQL literal so the admin handler stops passing them).

3. Create `backend/nodejs/src/repositories/appPlacesStats.repository.js`
   (a brand-new single-purpose repository file because
   `destinations.repository.js` does not own aggregate queries) with:
   - `getCategoryCounts()` — `SELECT category, COUNT(*) as count FROM app_places GROUP BY category` (exact SQL).
   - `getOverallRatingAverage()` — `SELECT AVG(rating) as avgRating FROM app_places` (exact SQL).

4. Replace the inline `db.*` calls in the three admin section files
   with calls to the new repository functions. Do **not** change any
   HTML output, validation, error path, or Vietnamese string. Do
   **not** consolidate the with-`?q=` and no-search branches into one
   query — the admin handler's behavior must stay exactly the same
   (separate SQL paths, separate parameter shapes).

5. The `POST /destinations/save` handler's image-upload /
   `place_images` / `place_id_map` logic does NOT exist today
   (the inline code only writes `app_places`), so there's no Phase-6
   image work being deferred from work item C — but be careful not to
   reorder the validation steps (`Number.isFinite(lat/lng)`,
   `nameTrim`/`descTrim` non-empty, `place_key=ADM_${newId}`,
   `shortDesc` truncation at 500 chars). They stay where they are.

**Forbidden in work item C.**

- Do not modify any existing repository function. Only add new ones.
- Do not change SQL semantics — column order, `?` placeholder count,
  parameter order, default-value literals (`'[]'`, `0`, `1`), and the
  exact whitespace inside multi-line SQL strings (newlines + leading
  spaces) all stay identical.
- Do not change column projections. If the admin route currently does
  `SELECT id, name, city, province, category, rating FROM app_places
  ORDER BY id DESC`, the new `listAdminDestinations()` selects exactly
  the same columns in exactly the same order. The admin templates
  render fields off the result rows by exact column name.
- Do not refactor the `bcrypt.hashSync(password, 10)` call in
  `POST /users/save`. That handler stays untouched in work item C.
- Do not extract the `POST /users/save` UPDATE/INSERT to the repo.
  Three independent code paths (idNum-with-password,
  idNum-without-password, new user) plus duplicate-email lookups
  through the existing `usersRepository.getUserIdByEmail{,ExcludingUser}`
  make this a Phase-6 / Phase-7 candidate.
- Do not extract the destination image / `place_id_map` writes. Those
  do not exist in the current `POST /destinations/save` (the admin UI
  doesn't upload images), and Phase 5 doesn't add them.
- Skip work item C entirely if you have any doubt about a specific
  query. The point is a low-risk continuation of the Phase 4 pilot,
  not a full sweep.

---

### 3.4 Work item D (OPTIONAL — only if A, B, and C are green) — admin router registration test

**Symptom.** Phase 4 verified the registration order of the 18 admin
routes by introspecting `router.stack` in the chat. That assertion
isn't captured anywhere in the test suite. If a future Phase 6 splits
the section files further (e.g. nests a sub-router) and accidentally
drops a route or reorders them, `npm test` won't notice.

**Required Phase-5 change.**

1. Create `backend/nodejs/tests/admin.router.test.js`. Boot the
   exported `buildAdminRouter()` factory (import it from
   `../src/admin/index.js` or from `../src/admin.js` — both work and
   both produce the same router).
2. Walk `router.stack`, extract `(method, path)` pairs from each
   `Layer.route` entry, and assert the array equals the documented
   18-tuple in exact order:
   ```
   GET    /dashboard
   GET    /users
   GET    /users/api/:id
   POST   /users/save
   POST   /users/delete/:id
   GET    /destinations
   GET    /destinations/api/:id
   POST   /destinations/save
   POST   /destinations/delete/:id
   GET    /system
   GET    /rag-ai
   POST   /rag-ai/reload-place-store
   POST   /rag-ai/clear-cache
   GET    /rag-ai/data-quality-issues
   GET    /rag-ai/ai-metrics
   GET    /rag-ai/ai-logs
   POST   /rag-ai/debug-query
   GET    /ai-report
   ```
3. Stub the DB before importing (vi.mock("../src/db.js", …)) the same
   way `health.test.js` does — the router factory calls into `db.js`
   on module load through the admin section files (they
   `import { db } from "../db.js"`), but `buildAdminRouter()` itself
   does not run any query at boot.

**Forbidden in work item D.**

- Do not boot the full `createApp()`. The admin section files import
  CSS/font URLs in their HTML templates but those are template
  literals, not network calls — booting the router alone is enough.
- Do not send any real HTTP request. This test asserts the
  registration shape, not the handler behavior. Handler tests are
  Phase 6+ scope.

Skip work item D if work item C was non-trivial. The registration
order is also stable enough that this test can wait.

---

## 4. Frozen contracts — do not violate

### 4.1 `/admin/*` URL contract

Same as Phase 4. Every path, request body field name, redirect target,
form field name, button label, table column, and Vietnamese string
visible in the rendered HTML is **frozen**. The 18 admin endpoints'
status codes and response types are unchanged from the Phase 4 result
table (§4.1 of `README_FIX_ALL_PHASE4.md`).

If work item C is performed, the SQL strings inside the new repository
functions must reproduce the inline SQL **exactly** (column projection,
parameter order, default-value literals, multi-line whitespace). The
admin templates render fields off the result rows by exact column
name, so any drift in the projection breaks the HTML.

### 4.2 RAG admin contract

Unchanged from Phase 4. `fetchRagJson` / `postRagJson` /
`formatRagFetchError` / `ragHeadersForPath` stay in
`src/admin/_shared/ragHttp.js` with the no-retry policy, 3000 ms / 5000
ms default timeouts, and the `{ ok, status, url, data }` envelope.

### 4.3 Android API contract

Phase 5 touches **only**:
- `src/routes/helpers.js` (split into a re-export shim — same export
  names, same function bodies) — see work item A.
- New files under `src/shared/dto/` (work item A).
- New files under `tests/` (work items B and D).
- New functions in `src/repositories/users.repository.js`,
  `src/repositories/destinations.repository.js`, and a new
  `src/repositories/appPlacesStats.repository.js` (work item C only).
- Existing inline `db.*` calls in three `src/admin/*.admin.routes.js`
  files are replaced with calls to the new repo functions (work item
  C only).

No file under `src/modules/` or `src/services/` is edited.
The 33 endpoints under `/api/**` are not modified.

### 4.4 DB schema & RAG service

- Schema (`backend/nodejs/database.sql`) is read-only reference. Not
  opened for writing.
- `backend/rag/**` is not touched.
- No Android source is touched.

---

## 5. Allowed files in Phase 5

### 5.1 Files you MAY EDIT

| File | Why |
| --- | --- |
| `backend/nodejs/src/routes/helpers.js` | Becomes a re-export shim after work item A. |
| `backend/nodejs/src/repositories/users.repository.js` | **Only if you do work item C.** Add new functions; do not modify existing ones. |
| `backend/nodejs/src/repositories/destinations.repository.js` | **Only if you do work item C.** Add new functions; do not modify existing ones. |
| `backend/nodejs/src/admin/users.admin.routes.js` | **Only if you do work item C.** Replace inline `db.query` listing calls with `usersRepository.*` calls. Handler body otherwise byte-identical. |
| `backend/nodejs/src/admin/destinations.admin.routes.js` | **Only if you do work item C.** Replace inline `db.{query,get,run}` listing + save calls with `destinationsRepository.*` calls. Handler body otherwise byte-identical. |
| `backend/nodejs/src/admin/aiReport.admin.routes.js` | **Only if you do work item C.** Replace inline `db.{query,get}` aggregate calls with the new `appPlacesStatsRepository.*` calls. |

### 5.2 Files you MAY CREATE

| File | Why |
| --- | --- |
| `backend/nodejs/src/shared/dto/userDto.js` | User DTO helpers (work item A). |
| `backend/nodejs/src/shared/dto/destinationDto.js` | Destination DTO helpers + `fixUrl` + `normalizeCategoryParam` (work item A). |
| `backend/nodejs/src/shared/dto/itineraryDto.js` | Itinerary DTO helpers (work item A). |
| `backend/nodejs/tests/adminAuth.middleware.test.js` | adminAuth behavior matrix (work item B). |
| `backend/nodejs/src/repositories/appPlacesStats.repository.js` | AI-report aggregates (work item C). |
| `backend/nodejs/tests/admin.router.test.js` | Admin registration shape (work item D). |

Total: up to six new files. Three for work item A, one for B, one
for C, one for D.

### 5.3 Files you MAY READ (for context)

- `README_FIX_ALL_PHASE5.md` (this file)
- `backend/nodejs/src/routes/helpers.js` (you will be splitting this)
- `backend/nodejs/src/middlewares/adminAuth.middleware.js` (read-only, you're testing it)
- `backend/nodejs/src/admin/index.js` and the six section files (read-only)
- `backend/nodejs/src/admin/{users,destinations,aiReport}.admin.routes.js` (work item C edits)
- `backend/nodejs/src/repositories/users.repository.js` (work item C reads + adds)
- `backend/nodejs/src/repositories/destinations.repository.js` (work item C reads + adds)
- `backend/nodejs/tests/health.test.js` (style template for work items B and D)
- `backend/nodejs/tests/ai-rag-chat.route.test.js` (style template for supertest usage)
- `backend/nodejs/src/utils.js` (`parseJsonArray` import path)
- `backend/nodejs/src/routes/auth.routes.js` (as a template for the Phase 5 re-export shim)

### 5.4 README append

You SHOULD append a `## 17. Phase 5 Result` section to
`README_FIX_ALL.md` at the repo root, mirroring the format of the
existing `## 16. Phase 4 Result` section. Keep it short: list files
changed, files created, work items completed, test results, and any
deferrals. Do NOT edit other sections of that file.

---

## 6. Forbidden files in Phase 5

Do **not** open for editing, create, or modify any of these:

- Anything under `backend/nodejs/src/modules/**` — Phase 2 module
  files, FROZEN. The eight import sites that reference
  `../routes/helpers.js` (or `../../routes/helpers.js`) continue to
  work through the shim; do NOT edit those imports.
- Anything under `backend/nodejs/src/services/**` — Phase 3
  transactional services, FROZEN. Same import-shim rule.
- Anything under `backend/nodejs/src/admin/_shared/**` and
  `backend/nodejs/src/admin/{dashboard,system,ragAi}.admin.routes.js`
  — Phase 4 admin shells / non-pilot sections, FROZEN.
- `backend/nodejs/src/admin.js` — Phase 4 shim, FROZEN.
- `backend/nodejs/src/admin/index.js` — Phase 4 factory, FROZEN.
- `backend/nodejs/src/routes/*.routes.js` — Phase 2 shims, FROZEN.
- `backend/nodejs/src/routes/index.js` — `registerApiRoutes`, FROZEN.
- `backend/nodejs/src/middlewares/**` — Phase 1 + Phase 4
  middlewares, FROZEN (including `adminAuth.middleware.js`; you may
  only test it, not edit it).
- `backend/nodejs/src/db.js`, `backend/nodejs/src/auth.js`,
  `backend/nodejs/src/utils.js`, `backend/nodejs/src/index.js`,
  `backend/nodejs/src/app.js`.
- `backend/nodejs/src/config/**`, `backend/nodejs/src/lib/**`,
  `backend/nodejs/src/schemas/**`.
- `backend/nodejs/src/shared/{http,db,utils}/**` — Phase 1 + Phase 3
  plumbing. The new `src/shared/dto/` directory IS allowed (work item
  A); existing subdirectories are not.
- `backend/nodejs/src/repositories/**` EXCEPT for adding new
  (non-modifying) functions in `users.repository.js` and
  `destinations.repository.js`, and EXCEPT for the brand-new
  `appPlacesStats.repository.js` file (work item C only). Other
  repository files remain untouched.
- `backend/nodejs/tests/{health,ai-rag-chat.route,ragContract,ragUpstream}.test.js`
  — Phase 1 baseline tests, FROZEN. Work items B and D add new test
  files; they do not modify the existing four.
- `backend/nodejs/package.json`, `backend/nodejs/package-lock.json`,
  `backend/nodejs/eslint.config.js`, `backend/nodejs/vitest.config.js`,
  `backend/nodejs/.prettierrc.json`, `backend/nodejs/database.sql`,
  `backend/nodejs/server.py`, `backend/nodejs/test_ai.js`,
  `backend/nodejs/seed.js`.
- All of `backend/rag/**` (FastAPI service).
- All Android sources (`app/**`, Gradle files, `local.properties`).
- The repo-root `.env` and `.env.example` — Phase 4 already documented
  the two ADMIN_BASIC_* placeholders.
- The parent `README_FIX_ALL.md` **except** for appending a new
  `## 17. Phase 5 Result` section at the end.
- `backend/nodejs/src/routes.js` (the deprecated re-export shim).
- The Phase 3 / Phase 4 plan docs `README_FIX_ALL_PHASE3.md` and
  `README_FIX_ALL_PHASE4.md`.
- This document `README_FIX_ALL_PHASE5.md` after Phase 5 ships.

---

## 7. Exact step-by-step plan

Recommended ordering (lowest risk first):

1. **Work item A**, in this sub-order:
   1. Read `src/routes/helpers.js` fully. Note the dependency direction
      (`toUserDto` → `fixUrl`; `getDestinationImages` → `fixUrl`;
      `attachDestinationImages` → `fixUrl`; `resolveDestinationIdsFromSelection`
      → `placeIdMapRepository`).
   2. Create `src/shared/dto/destinationDto.js` FIRST (because
      `userDto.js` will import `fixUrl` from it). Move `fixUrl`,
      `getImageUrlValue`, `getDestinationImages`,
      `attachDestinationImages`, `normalizeCategoryParam`, and
      `toDestinationDto` verbatim. Run `npm test` and `npm run lint`.
   3. Create `src/shared/dto/userDto.js`. Move `toUserDto`,
      `getUserById`, `firstArrayValue` verbatim. Import `fixUrl` from
      `./destinationDto.js`. Run `npm test` and `npm run lint`.
   4. Create `src/shared/dto/itineraryDto.js`. Move
      `flattenSelectedOptionDays`, `resolveDestinationIdsFromSelection`,
      `itineraryRowToDto` verbatim. Adjust the
      `placeIdMapRepository` import path (one extra `..`). Run
      `npm test` and `npm run lint`.
   5. Replace `src/routes/helpers.js` with the re-export shim. Verify
      it exports exactly the same 10 names with the same shapes by
      booting the app factory and importing every consumer file.
2. **Work item B** — add `tests/adminAuth.middleware.test.js`. Run
   `npm test` and confirm the suite now reports `5 passed (5)` /
   `Tests N passed` where N = 7 + (number of new `it(…)` cases).
3. (Optional) **Work item C** — admin SQL sweep, in this sub-order:
   1. users listing queries → `users.repository.js` (`listAdminUsers`,
      `searchAdminUsers`). Replace inline `db.query` calls. Run
      `npm test`.
   2. destinations listing queries → `destinations.repository.js`
      (`listAdminDestinations`, `searchAdminDestinations`). Replace
      inline `db.query` calls. Run `npm test`.
   3. destinations save (UPDATE) → `updateAdminDestination(...)`.
      Replace inline `db.run`. Run `npm test`.
   4. destinations save (next-id + INSERT) → `getNextAppPlaceId()` and
      `insertAdminDestination(...)`. Replace inline `db.get` +
      `db.run`. Run `npm test`.
   5. ai-report aggregates → new
      `src/repositories/appPlacesStats.repository.js` with
      `getCategoryCounts()` + `getOverallRatingAverage()`. Replace
      inline `db.query` + `db.get`. Run `npm test`.
4. (Optional) **Work item D** — add `tests/admin.router.test.js`. Run
   `npm test`.
5. Append `## 17. Phase 5 Result` to `README_FIX_ALL.md`.
6. Stop. Do not start Phase 6.

After each work item, confirm the working tree is sane:

```powershell
cd E:\UNUtrip\backend\nodejs
npm test
npm run lint
```

If any test or lint check fails, stop and revert the most recent
change with `git restore <file>` and `git clean -fd backend/nodejs/src/shared/dto/`
(or the relevant new directory) — do NOT commit failures.

---

## 8. Verification checklist

Run from `backend/nodejs/` unless noted.

### 8.1 Unit tests

```powershell
cd E:\UNUtrip\backend\nodejs
npm test
```

Phase 5 baseline (work item B done, work item D not done) must show:

```
Test Files  5 passed (5)
     Tests  N passed (N)
```

where `N >= 7 + 9` (the existing 7 plus at least 9 new `it(…)` cases
listed in §3.2.3). If work item D is also done, expect
`Test Files 6 passed (6)`.

### 8.2 Lint

```powershell
npm run lint
```

Must report no findings.

### 8.3 helpers.js shim smoke (highly recommended)

Boot Node and import every consumer file to confirm no consumer breaks
on the shim:

```powershell
node -e "import('./src/modules/auth/auth.controller.js').then(() => import('./src/modules/users/users.controller.js')).then(() => import('./src/modules/destinations/destinations.controller.js')).then(() => import('./src/services/destinations.service.js')).then(() => import('./src/services/favorites.service.js')).then(() => import('./src/services/itineraries.service.js')).then(() => import('./src/services/reviews.service.js')).then(() => console.log('all consumers import OK')).catch(e => { console.error('FAIL', e); process.exit(1); });"
```

Expected: `all consumers import OK`.

### 8.4 helpers.js shape parity

Optional but reassuring — dump the export shape of the old vs new
`helpers.js` and confirm all 10 names are present:

```powershell
node -e "import('./src/routes/helpers.js').then(m => { const want = ['toUserDto','getUserById','firstArrayValue','toDestinationDto','attachDestinationImages','fixUrl','normalizeCategoryParam','itineraryRowToDto','flattenSelectedOptionDays','resolveDestinationIdsFromSelection']; const got = Object.keys(m).sort(); const missing = want.filter(n => !got.includes(n)); console.log({missing, totalGot: got.length}); });"
```

Expected: `{ missing: [], totalGot: 10 }`.

### 8.5 File-level sanity

```powershell
# After Phase 5, routes/helpers.js is a few lines (re-export shim).
(Get-Content backend\nodejs\src\routes\helpers.js | Measure-Object -Line).Lines    # expect < 30

# shared/dto/ contains the three new DTO files.
Get-ChildItem backend\nodejs\src\shared\dto | Where-Object { -not $_.PsIsContainer } | Measure-Object | Select-Object -Expand Count
# expect 3

# adminAuth test exists.
Test-Path backend\nodejs\tests\adminAuth.middleware.test.js

# git status only shows files inside the allow-list.
git status
```

---

## 9. Pass criteria

Phase 5 is done when **ALL** of the below are true:

1. Work items A and B are implemented.
2. `npm test` shows at minimum `Test Files 5 passed (5)` with the
   new adminAuth test file adding at least 9 `it(…)` cases. The
   previous 4 test files keep their counts unchanged (no regression).
3. `npm run lint` is clean.
4. `git status` shows changes ONLY in the files listed in §5.1 / §5.2
   (plus the appended `## 17. Phase 5 Result` section in
   `README_FIX_ALL.md`).
5. The rendered HTML of every `/admin/*` page is byte-identical to
   pre-Phase-5 output (timestamps and live counters excepted).
6. The JSON responses of every JSON admin endpoint **and** every
   `/api/**` endpoint are byte-identical to pre-Phase-5 output.
7. The `routes/helpers.js` shim re-exports all 10 original names with
   the same function bodies (verified via §8.4).
8. With Phase 4's env-gated adminAuth still in place, the
   `/admin/*` mount behaves the same as before: default-open when
   env vars are unset (with a one-time warning), gated when set.
9. `src/routes/helpers.js` is a re-export shim (< 30 lines).
10. No edits to any file listed in §6.
11. No new dependency added to `package.json`.
12. Repository public APIs are unchanged for any existing function.
    Work item C adds new functions only; existing function
    signatures and return shapes are unchanged.
13. Admin router still registers the same 18 routes in the same
    order — verified by work item D's test, or by an inline
    introspection of `router.stack` if D is skipped.

## 9.1 Fail criteria — stop immediately if any of these happen

- A test that passed before Phase 5 now fails.
- An admin or `/api/**` endpoint returns a different status code, a
  different response shape, or different HTML than before.
- The `routes/helpers.js` shim loses one of the 10 original exports.
- A file listed in §6 was edited.
- A new dependency was added to `package.json`.
- A consumer of `routes/helpers.js` (or one of the new DTO modules)
  receives a circular-import warning at boot.
- The new test file fails to isolate the `warned` module-level guard
  inside `adminAuth.middleware.js`, causing the
  "one-time warning" assertion to be order-dependent across `it(…)`
  cases.

If any of these happen, revert the offending change with
`git restore <file>` and (for newly-created files)
`git clean -fd backend/nodejs/src/shared/dto/ backend/nodejs/tests/`
then re-evaluate before continuing.

---

## 10. Handoff prompt for the new agent

> Copy/paste exactly this into the new Cursor Agent chat. Do not abbreviate.

```
You are continuing the UnuTrip graduation-project backend refactor.

CONTEXT:
- Repo root: E:\UNUtrip.
- The Node backend lives in backend/nodejs/.
- There is a Phase 5 plan at repo root: README_FIX_ALL_PHASE5.md.
- Phase 1 (shared plumbing), Phase 2 (module shell migration for
  /api/**), Phase 3 (AI/itinerary transactional hardening), and
  Phase 4 (admin module shell + HTTP Basic Auth gate) have already
  been completed and committed. Working tree is clean.
- An Android app consumes backend/nodejs over HTTP. backend/nodejs
  proxies AI work to backend/rag. The current system works and must
  not break.
- src/routes/helpers.js is a 263-line grab-bag exporting 10 names
  across three unrelated domains (user DTO, destination DTO,
  itinerary DTO). It is imported by 8 files in src/modules/ and
  src/services/. Phase 5 splits it into per-domain DTO modules.
- Phase 4 added src/middlewares/adminAuth.middleware.js but no
  automated test covers it. Phase 5 adds that coverage.
- Phase 4 piloted only the simplest two admin SQL queries per file.
  The remaining inline db.* calls in admin user/destination/aiReport
  routes are still there. Phase 5 optionally continues that pilot.

TASK:
1. Read README_FIX_ALL_PHASE5.md fully. Treat it as the authoritative
   plan. You do NOT need to read README_FIX_ALL.md unless the
   Phase 5 plan references a specific section of it.
2. Implement Phase 5 exactly as described:
   - Work items A and B are REQUIRED.
   - Work items C and D are OPTIONAL — only do them if A and B land
     green with the test suite still passing.
3. Touch ONLY the files listed in section 5.1 ("Allowed files: MAY
   EDIT") and at most six new files from section 5.2 ("MAY CREATE").
4. Do NOT touch any file listed in section 6 ("Forbidden files in
   Phase 5"), especially: modules/**, services/**, the existing
   admin _shared/** and admin shells (only the three admin section
   files mentioned in §5.1 may be edited, and only inside work item
   C), middlewares/** (you only TEST adminAuth — never edit it),
   db.js, auth.js, utils.js, app.js, index.js, config/**, lib/**,
   schemas/**, the existing shared/{http,db,utils}/** subtrees,
   tests/{health,ai-rag-chat.route,ragContract,ragUpstream}.test.js,
   package.json, backend/rag, Android sources, .env, .env.example.
5. Preserve every byte of rendered HTML, every JSON response shape,
   every URL path, every redirect target, every form field name, and
   every Vietnamese string under /admin/** and /api/**. Function
   bodies in the new DTO modules must be byte-identical copies of
   the originals in routes/helpers.js.
6. Do not modify the database schema or any existing repository /
   DTO / service / module function. New repository functions (work
   item C) may be ADDED but not modified. New DTO modules (work item
   A) hold byte-identical copies of the original helpers — the
   helpers.js file itself becomes a re-export shim.
7. After each work item, run `npm test` AND `npm run lint` from
   backend/nodejs/. If anything regresses, revert and stop.
8. After all required work items are done, append a "Phase 5 Result"
   section to README_FIX_ALL.md (section 17). Then STOP. Do not
   start Phase 6.
9. If you encounter any ambiguity, stop and ask the user before
   writing code. Especially: if any Vietnamese string in admin HTML
   looks like it might be wrong, do NOT "fix" it — copy it verbatim.
   If any SQL string in the inline admin code looks suspicious, do
   NOT "clean it up" while extracting it to a repository — copy
   it verbatim.

DELIVERABLES:
- New files under backend/nodejs/src/shared/dto/ (work item A):
  userDto.js, destinationDto.js, itineraryDto.js. Each contains
  byte-identical copies of the original function bodies from
  src/routes/helpers.js.
- backend/nodejs/src/routes/helpers.js reduced to a one-line
  re-export shim that exposes all 10 original names from the three
  new DTO modules (work item A). Eight existing import sites
  continue to work through the shim unchanged — do NOT edit those
  import sites.
- New file backend/nodejs/tests/adminAuth.middleware.test.js (work
  item B). At least 9 it(…) cases covering the dev-mode passthrough,
  the one-time warning guard, and the gated-mode 401 / 200 matrix
  enumerated in §3.2 of the plan.
- Optionally: new exported functions in
  backend/nodejs/src/repositories/users.repository.js and
  backend/nodejs/src/repositories/destinations.repository.js, and a
  brand-new backend/nodejs/src/repositories/appPlacesStats.repository.js
  file (work item C). Inline db.* calls in the three admin section
  files (users, destinations, aiReport) replaced with the new repo
  calls. Handler bodies otherwise byte-identical.
- Optionally: new file backend/nodejs/tests/admin.router.test.js
  (work item D) asserting all 18 admin routes register in the
  documented order.
- A short append to README_FIX_ALL.md describing what shipped
  (section 17).
- Test result + lint result + summary of changes.

Start now by reading README_FIX_ALL_PHASE5.md only, then list the
files you intend to edit and create, then proceed.
```

---

*End of `README_FIX_ALL_PHASE5.md`. After Phase 5 ships, this document
remains in the repo as historical context; it does not need to be
updated. Phase 6 will get its own handoff doc
(`README_FIX_ALL_PHASE6.md`) when the time comes.*
