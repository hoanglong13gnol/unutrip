# README_FIX_ALL_PHASE4.md

> Handoff document for **Phase 4 of the UnuTrip backend refactor**.
> Audience: a fresh Cursor Agent that has **no prior chat context** and must
> implement Phase 4 in safe, behavior-preserving steps.
> Repository root: `E:\UNUtrip` (Windows / PowerShell, also runs on POSIX).
> This document is the **single source of truth** for Phase 4. The parent
> document `README_FIX_ALL.md` is informational context only; you do **not**
> need to open it to do Phase 4 — everything you need is here.

---

## 1. Mission

**Phase 4 = Admin module shell migration + admin auth.**

The current `backend/nodejs/src/admin.js` file is ~2000 lines that mix
HTML rendering, inline SQL (16 direct `db.{query,get,run}` calls),
RAG fetch helpers, password hashing, validation, and category
normalization. Phase 4 cleans up the **shape** of that file without
touching its **behavior**:

1. **Split `src/admin.js`** into a thin `src/admin/index.js` that
   instantiates `express.Router()` and registers per-section route
   modules under `src/admin/<section>.admin.routes.js`. Mirror the
   Phase 2 module-shell migration pattern: handler bodies are **byte-
   identical copies** of the originals. Shared helpers (`escapeHtml`,
   `renderLayout`, `renderJsonBox`, `APP_PLACE_CATEGORY_ENUM`,
   `normalizeAppPlaceCategory`, `formatRagFetchError`,
   `ragHeadersForPath`, `fetchRagJson`, `postRagJson`) move into
   `src/admin/_shared/*.js`.
2. **Add `adminAuth.middleware.js`** (env-gated HTTP Basic Auth) and
   wire it into `app.js` immediately before the `/admin` mount.
   Default-off behavior is preserved when `ADMIN_BASIC_USER` /
   `ADMIN_BASIC_PASS` are unset; a one-time warning is logged.
3. **(Optional, only if 1–2 land green)** Replace ONE section's
   inline `db.{query,get,run}` calls with new admin-scoped repository
   functions added to the existing `users.repository.js` (do NOT
   create new repository files). Pilot only — do not refactor every
   section.
4. **(Optional, only if 1–3 are green)** Repeat the pilot for ONE more
   section (likely `destinations`) by adding helper functions to the
   existing `destinations.repository.js`.

**Goal:** preserve every byte of the rendered HTML, the JSON responses,
the redirect URLs, the form field names, the Vietnamese strings, and
the RAG admin contract. After Phase 4, every URL under `/admin/*`
returns the same status code, the same headers, and the same body as
before.

**Non-goals (forbidden in Phase 4):**

- **Do not** change any rendered HTML byte-for-byte. Tailwind classes,
  inline `<script>` blocks, button labels, Vietnamese copy, table
  columns, form field names, and the layout structure are all frozen.
- **Do not** change any `/admin/*` URL path, request body field name,
  redirect target, or HTTP status code.
- **Do not** extract HTML to external `.html` template files — that is
  Phase 5 work. Templates remain inline in JS template literals.
- **Do not** tighten the helmet CSP. The `'unsafe-inline'` /
  `scriptSrcAttr` allowances stay because inline `<script>` blocks are
  still present in admin templates.
- **Do not** modify the Android-facing API contract under `/api/**`.
- **Do not** modify the RAG upstream contract.
- **Do not** modify the database schema.
- **Do not** touch `backend/rag/**` (FastAPI service).
- **Do not** touch any Android source (`app/`, Gradle files, etc.).
- **Do not** add new dependencies.
- **Do not** rewrite `fetchRagJson` / `postRagJson` to use
  `src/lib/ragUpstream.js`. Those admin helpers intentionally have
  no retry logic (operators need raw upstream errors). Keep them
  retry-less; just relocate them into `src/admin/_shared/ragHttp.js`.
- **Do not** edit `package.json`, `package-lock.json`, `database.sql`,
  `eslint.config.js`, `vitest.config.js`, any `.prettierrc.json`, or
  any file under `src/config/`, `src/lib/`, `src/schemas/`,
  `src/middlewares/` (except creating the new `adminAuth.middleware.js`),
  or `src/shared/`.
- **Do not** modify `.env` (operator-managed). Appending two
  commented lines to `.env.example` IS allowed as documentation —
  see §3.2.

---

## 2. Current state (after Phase 1 + Phase 2 + Phase 3, already committed)

Three prior commits land before Phase 4:

| Commit | What it did |
| --- | --- |
| `c8bade9` — **Phase 1** | Added shared kit: `HttpError`, `asyncHandler`, `apiOk/apiFail/apiList`, `withTransaction`, plus `requestId` / `notFound` / `errorHandler` middlewares wired into `app.js`. |
| `2057944` — **Phase 2** | Moved all 8 feature routes from `src/routes/*.routes.js` into `src/modules/<feature>/{routes,controller}.js`. The old `routes/*.routes.js` files are now one-line re-export shims. |
| **Phase 3** (uncommitted at time of writing this doc, see §15 of `README_FIX_ALL.md`) | Wrapped the AI-itinerary persistence flows in `withTransaction`, added `persistAiSuggestedItinerary`, dropped the PII `console.log` in `saveAiItinerary`, and extracted `DEFAULT_AI_ITINERARY_TIME_SLOTS`. No admin file was touched. |

You should start Phase 4 with a **clean working tree** on branch
`v2/database-refactor`. Verify with `git status` before starting.

### Layer map (as of start of Phase 4)

```
backend/nodejs/src/
├── app.js                              Express factory (mounts /api and /admin)
├── index.js                            HTTP listener
├── routes.js                           one-line re-export of ./routes/index.js (legacy)
├── routes/                             API routes (Phase 2 shims + index.js)
├── modules/                            API controllers/routes (Phase 2)
├── services/                           service layer (Phase 3 transactional)
├── repositories/                       repository layer (FROZEN in Phase 4)
├── shared/                             Phase 1 plumbing + Phase 3 utils
├── middlewares/                        Phase 1 middlewares (Phase 4 adds adminAuth)
├── config/, lib/, schemas/, auth.js, db.js, utils.js   ALL FROZEN
├── admin.js                            << Phase 4 must split this file
└── seed.js, data/                      FROZEN
```

After Phase 4 the layout becomes:

```
backend/nodejs/src/
├── admin.js                            one-line re-export shim (Phase 4)
├── admin/
│   ├── index.js                        buildAdminRouter() — registers section routers
│   ├── _shared/
│   │   ├── escape.js                   escapeHtml, renderJsonBox
│   │   ├── categories.js               APP_PLACE_CATEGORY_ENUM, normalizeAppPlaceCategory
│   │   ├── ragHttp.js                  formatRagFetchError, ragHeadersForPath, fetchRagJson, postRagJson
│   │   └── layout.js                   renderLayout
│   ├── dashboard.admin.routes.js       GET /dashboard
│   ├── users.admin.routes.js           GET /users, GET /users/api/:id, POST /users/save, POST /users/delete/:id
│   ├── destinations.admin.routes.js    GET /destinations, GET /destinations/api/:id, POST /destinations/save, POST /destinations/delete/:id
│   ├── system.admin.routes.js          GET /system
│   ├── ragAi.admin.routes.js           GET /rag-ai, POST /rag-ai/reload-place-store, POST /rag-ai/clear-cache, GET /rag-ai/data-quality-issues, GET /rag-ai/ai-metrics, GET /rag-ai/ai-logs, POST /rag-ai/debug-query
│   └── aiReport.admin.routes.js        GET /ai-report
├── middlewares/
│   └── adminAuth.middleware.js         (new)
└── ... (everything else unchanged)
```

---

## 3. What Phase 4 must do — the work items

### 3.1 Work item A (REQUIRED) — split `admin.js` into per-section modules

**Symptom.** `src/admin.js` is 1997 lines covering eighteen distinct
admin endpoints, four private RAG helpers, two category helpers, three
HTML helpers, and one giant `renderLayout` function. Every change to
any admin section currently risks touching unrelated code.

**Required Phase-4 change.**

1. Create `backend/nodejs/src/admin/_shared/escape.js`:
   ```js
   export function escapeHtml(value) { /* byte-identical body */ }
   export function renderJsonBox(value) { /* byte-identical body */ }
   ```
   Move these two functions out of `admin.js` verbatim. `renderJsonBox`
   already calls `escapeHtml(JSON.stringify(...))` — keep the call.

2. Create `backend/nodejs/src/admin/_shared/categories.js`:
   ```js
   export const APP_PLACE_CATEGORY_ENUM = new Set([ /* 10 strings */ ]);
   export function normalizeAppPlaceCategory(category) { /* byte-identical body */ }
   ```
   Move both out of `admin.js` verbatim. Do not change the set
   contents, the `"historical" → "heritage"` mapping, the
   `"entertainment" → "other"` mapping, or the `"other"` default.

3. Create `backend/nodejs/src/admin/_shared/ragHttp.js`:
   ```js
   import {
     ragAdminJsonHeaders,
     ragJsonHeaders,
     ragUrl
   } from "../../config/ragClient.js";

   export function formatRagFetchError(error) { /* byte-identical */ }
   export function ragHeadersForPath(pathname) { /* byte-identical */ }
   export async function fetchRagJson(pathname, timeoutMs = 3000) { /* byte-identical */ }
   export async function postRagJson(pathname, body = {}, timeoutMs = 5000) { /* byte-identical */ }
   ```
   - Keep `AbortController` + `setTimeout` + `clearTimeout` exactly as
     the originals. Keep the `JSON.parse(text)` try/catch returning
     `{ raw: text }` on parse failure. Keep the error envelope
     `{ ok:false, status:0, url, data:{ error } }`.
   - Default timeouts must remain `3000` (GET) and `5000` (POST).
   - Do **not** add retries. Do **not** use `ragPostJson` from
     `src/lib/ragUpstream.js`. Admin operators rely on the raw
     upstream error shape — no retry semantics are allowed.

4. Create `backend/nodejs/src/admin/_shared/layout.js`:
   ```js
   import { escapeHtml } from "./escape.js";
   export function renderLayout(content, activePath, title = "Quản trị hệ thống") { /* byte-identical body */ }
   ```
   - Default `title` argument must remain the Vietnamese string
     `"Quản trị hệ thống"`.
   - The active-tab highlighting logic (matching `activePath`) and
     every Tailwind class must remain identical.
   - All Vietnamese labels in the navbar (`"Tổng quan"`, `"Người
     dùng"`, `"Địa điểm"`, `"Hệ thống"`, `"RAG / AI"`, `"Báo cáo AI"`)
     are byte-frozen.

5. Create one route module per admin section under `src/admin/`. Each
   file exports a `register*AdminRoutes(router)` function that calls
   `router.get(...)` / `router.post(...)` with handlers that are
   **byte-identical** to the bodies currently in `admin.js`. Path
   strings, status codes, redirect targets, and rendered HTML are all
   frozen.

   | New file | Routes handled (paths shown without the `/admin` mount prefix) |
   | --- | --- |
   | `src/admin/dashboard.admin.routes.js` | `GET /dashboard` |
   | `src/admin/users.admin.routes.js` | `GET /users`, `GET /users/api/:id`, `POST /users/save`, `POST /users/delete/:id` |
   | `src/admin/destinations.admin.routes.js` | `GET /destinations`, `GET /destinations/api/:id`, `POST /destinations/save`, `POST /destinations/delete/:id` |
   | `src/admin/system.admin.routes.js` | `GET /system` |
   | `src/admin/ragAi.admin.routes.js` | `GET /rag-ai`, `POST /rag-ai/reload-place-store`, `POST /rag-ai/clear-cache`, `GET /rag-ai/data-quality-issues`, `GET /rag-ai/ai-metrics`, `GET /rag-ai/ai-logs`, `POST /rag-ai/debug-query` |
   | `src/admin/aiReport.admin.routes.js` | `GET /ai-report` |

   Inside each section file, import only the helpers it actually needs
   from `./_shared/*.js` and from the existing repositories /
   `db.js` / `config/*` exactly as `admin.js` does today. Do **not**
   inline a helper that already exists in `_shared/`.

6. Create `backend/nodejs/src/admin/index.js`:
   ```js
   import { Router } from "express";
   import { registerDashboardAdminRoutes } from "./dashboard.admin.routes.js";
   import { registerUsersAdminRoutes } from "./users.admin.routes.js";
   import { registerDestinationsAdminRoutes } from "./destinations.admin.routes.js";
   import { registerSystemAdminRoutes } from "./system.admin.routes.js";
   import { registerRagAiAdminRoutes } from "./ragAi.admin.routes.js";
   import { registerAiReportAdminRoutes } from "./aiReport.admin.routes.js";

   export function buildAdminRouter() {
     const router = Router();
     registerDashboardAdminRoutes(router);
     registerUsersAdminRoutes(router);
     registerDestinationsAdminRoutes(router);
     registerSystemAdminRoutes(router);
     registerRagAiAdminRoutes(router);
     registerAiReportAdminRoutes(router);
     return router;
   }
   ```
   - Registration order **must match** the order the handlers appear
     in today's `admin.js` so any path-overlap precedence is
     preserved. (As of today there is no overlap, but order matters
     defensively.)
   - `buildAdminRouter()` must still return an `express.Router()`
     instance — the current caller in `app.js`
     (`app.use("/admin", buildAdminRouter())`) is locked.

7. Replace `backend/nodejs/src/admin.js` with a single-line re-export
   shim — mirror the Phase 2 pattern used for `routes/*.routes.js`:
   ```js
   /**
    * Phase 4 compatibility shim — implementation moved to
    * `src/admin/index.js`.
    * Kept as a re-export so any external import of this path keeps working.
    */
   export { buildAdminRouter } from "./admin/index.js";
   ```
   The original 1997-line file is **deleted in place** and replaced
   with this shim. `app.js`'s `import { buildAdminRouter } from
   "./admin.js"` continues to work unchanged.

**Forbidden in work item A.**

- Do not change a single byte of any rendered HTML. (If you wanted to
  fix a typo in a Vietnamese label, do not.)
- Do not change SQL strings inside any inline `db.{query,get,run}`
  call (those refactors are work items C / D, both optional).
- Do not change default timeouts (`3000` GET, `5000` POST).
- Do not move the inline `<script>` blocks. They stay inside the
  template literals.
- Do not introduce TypeScript, JSDoc generics, or default exports.
- Do not change the `bcrypt` cost or password-hash usage in
  `users.admin.routes.js`.
- Do not collapse the eight `getX` Promise.all blocks in `dashboard`,
  `system`, or `rag-ai` — they are intentionally parallel.

---

### 3.2 Work item B (REQUIRED) — add `adminAuth.middleware.js`

**Symptom.** `/admin/*` currently has **no authentication at all**.
Anyone who can reach the Node port can hit `/admin/users/delete/:id`.
This is acceptable for a dev demo but not for a graduation submission.

**Required Phase-4 change.**

1. Create `backend/nodejs/src/middlewares/adminAuth.middleware.js`:
   ```js
   /**
    * HTTP Basic Auth gate for /admin/*.
    *
    * - Enabled when BOTH `ADMIN_BASIC_USER` and `ADMIN_BASIC_PASS`
    *   are present in process.env.
    * - Disabled (passthrough + one-time stderr warning) when either
    *   is missing — preserves the existing default-open behavior so
    *   running the project locally without setting the vars still
    *   works for the demo.
    *
    * The middleware does NOT call any DB or RAG service. It only
    * decodes the Authorization: Basic header and constant-time-
    * compares the credentials.
    */
   ```
   Behavior contract:
   - At module load, log **once** to `console.warn` if either env var
     is missing: `"[adminAuth] ADMIN_BASIC_USER/ADMIN_BASIC_PASS not set — /admin is unauthenticated (dev mode)"`. Use a module-level
     `let warned = false` guard so repeated test imports do not spam.
   - If both env vars are set:
     - Read `req.headers.authorization`. If missing or not
       `Basic <base64>`, respond `401` with header
       `WWW-Authenticate: Basic realm="UnuTrip Admin"` and body
       `Unauthorized`.
     - Decode base64 to `user:pass`. If `user !== ADMIN_BASIC_USER` or
       `pass !== ADMIN_BASIC_PASS`, respond `401` with the same
       header and body. Use a constant-time compare (e.g.
       `crypto.timingSafeEqual(Buffer.from(a), Buffer.from(b))` after
       length-padding) to defeat trivial timing attacks.
     - Otherwise call `next()`.
   - Export a named function `adminAuthMiddleware(req, res, next)`.
2. Wire the middleware in `backend/nodejs/src/app.js`:
   ```js
   import { adminAuthMiddleware } from "./middlewares/adminAuth.middleware.js";
   // ...
   app.use("/admin", adminAuthMiddleware, buildAdminRouter());
   ```
   The only change to `app.js` is (a) adding the import line and
   (b) inserting `adminAuthMiddleware` between the mount path and
   `buildAdminRouter()`. Do not touch any other line in `app.js`.

3. Append two **commented** documentation lines to the existing
   `.env.example` at the repo root (do not uncomment them — the
   default must remain dev-mode-open):
   ```
   # ADMIN_BASIC_USER=
   # ADMIN_BASIC_PASS=
   ```
   Place them after the existing `RAG_ADMIN_API_KEY` line so all
   admin-scoped vars cluster together. Do not modify any other line
   of `.env.example`. Do not create or touch `.env`.

**Forbidden in work item B.**

- Do not change the env-var names (`ADMIN_BASIC_USER`,
  `ADMIN_BASIC_PASS`) — they are documented in this file for
  operators.
- Do not enable the middleware by default. If the operator does not
  set both vars, `/admin/*` must remain accessible (with the warning
  logged once).
- Do not add the middleware to `src/config/env.js`. It reads
  `process.env` directly so `config/env.js` stays frozen.
- Do not use `express-basic-auth` or any new npm dependency. Use
  Node's built-in `Buffer.from(..., "base64")` and `crypto`.
- Do not require the user to log in via a form. HTTP Basic over
  HTTPS is intentionally chosen for simplicity; the browser handles
  the prompt.
- Do not return JSON on 401 — return plain text `Unauthorized` (the
  browser uses the `WWW-Authenticate` header, not the body).

---

### 3.3 Work item C (OPTIONAL — only if A and B are green) — pilot users-admin repository extraction

**Symptom.** The `users.admin.routes.js` handlers (the four routes
listed in work item A) currently make direct `db.query` /
`db.get` / `db.run` calls inline. Three of those queries are simple
parameterized selects/aggregates that already have natural homes
in the existing `src/repositories/users.repository.js`.

**Required Phase-4 change.**

1. Identify the exact inline `db.*` calls in `users.admin.routes.js`
   that read **plain user-table** data:
   - The `LIMIT/OFFSET` listing query on `users` plus its
     `COUNT(*)` companion.
   - The `WHERE id = ?` lookup that powers `GET /users/api/:id`.
   - The `DELETE FROM users WHERE id = ?` statement in
     `POST /users/delete/:id`.
2. Add new exported functions to
   `backend/nodejs/src/repositories/users.repository.js` that
   reproduce each query exactly (parameter shape, SQL text,
   `lastInsertRowid` / `changes` field names). Pick names that follow
   the existing convention (e.g. `listUsersPaged({ limit, offset })`,
   `countAllUsers()`, `getUserRowById(id)`, `deleteUserById(id)`).
3. Replace the inline `db.*` calls in `users.admin.routes.js` with
   calls to the new repository functions. Do not change any HTML
   output, validation, or error path.
4. Do **not** modify any other section's inline SQL in Phase 4. The
   point is a low-risk pilot, not a full sweep.

**Forbidden in work item C.**

- Do not rename existing functions in `users.repository.js`. Only
  add new ones.
- Do not change SQL semantics (LIMIT/OFFSET, COUNT(*), DELETE … WHERE
  id) — the result rows admin templates depend on must remain
  identical.
- Do not change column projections. If admin currently selects
  `SELECT id, full_name, email, phone, created_at FROM users …`,
  the new repository function selects exactly the same columns in
  exactly the same order.
- Do not refactor `bcrypt` calls in `users/save`. Password hashing
  stays inline in the handler; the repository receives the already-
  hashed string.

Skip work item C if you have any doubt about a specific query — the
risk-to-reward ratio is unfavorable when admin templates render fields
directly off the row object.

---

### 3.4 Work item D (OPTIONAL — only if A, B, and C are green) — pilot destinations-admin repository extraction

Same pattern as work item C, applied to `destinations.admin.routes.js`
(the four routes listed in work item A). Add new functions to the
existing `src/repositories/destinations.repository.js`. Likely
candidates:

- The paged listing on `app_places` with optional category filter.
- The single-row `GET /destinations/api/:id` lookup.
- The `DELETE FROM app_places WHERE id = ?` statement.

The `POST /destinations/save` handler is **excluded** from this
extraction — it touches `app_places`, `place_images`, and the
`place_id_map` linkage. That refactor belongs to Phase 5 alongside the
broader admin repository sweep.

**Forbidden in work item D.**

- Same constraints as work item C.
- Do not touch the image-upload / `place_images` reconciliation logic.
- Do not touch the `place_id_map` insert/update logic.

Skip work item D if work item C was non-trivial or if you ran out of
time. The duplication is harmless until Phase 5.

---

## 4. Frozen contracts — do not violate

### 4.1 `/admin/*` URL contract

Every path, request body field name, redirect target, form field name,
button label, table column, and Vietnamese string visible in the
rendered HTML is **frozen**. The eighteen admin endpoints and their
expected response types are:

| Method | Path | Owner section (after Phase 4) | Response |
| --- | --- | --- | --- |
| GET | `/admin/dashboard` | dashboard | HTML 200 |
| GET | `/admin/users` | users | HTML 200 (with optional `?page=&q=` query params) |
| GET | `/admin/users/api/:id` | users | `{ success, data }` JSON 200 / `{ success:false, message }` 404 |
| POST | `/admin/users/save` | users | Redirect 302 to `/admin/users` on success, or HTML 400 |
| POST | `/admin/users/delete/:id` | users | Redirect 302 to `/admin/users` |
| GET | `/admin/destinations` | destinations | HTML 200 (with optional `?page=&q=&category=`) |
| GET | `/admin/destinations/api/:id` | destinations | JSON 200 / 404 |
| POST | `/admin/destinations/save` | destinations | Redirect 302 to `/admin/destinations` |
| POST | `/admin/destinations/delete/:id` | destinations | Redirect 302 to `/admin/destinations` |
| GET | `/admin/system` | system | HTML 200 |
| GET | `/admin/rag-ai` | ragAi | HTML 200 |
| POST | `/admin/rag-ai/reload-place-store` | ragAi | JSON proxy of RAG admin response |
| POST | `/admin/rag-ai/clear-cache` | ragAi | JSON proxy of RAG admin response |
| GET | `/admin/rag-ai/data-quality-issues` | ragAi | JSON proxy |
| GET | `/admin/rag-ai/ai-metrics` | ragAi | JSON proxy |
| GET | `/admin/rag-ai/ai-logs` | ragAi | JSON proxy |
| POST | `/admin/rag-ai/debug-query` | ragAi | JSON (combined RAG + local-AI result) |
| GET | `/admin/ai-report` | aiReport | JSON `{ success, report }` or `{ success:false, message }` |

All eighteen handlers' bodies must be **byte-identical** to today's
`admin.js` after the split. Use `git diff --stat` and a spot-check
diff to confirm.

### 4.2 RAG admin contract

The four wrapper functions `fetchRagJson` / `postRagJson` /
`formatRagFetchError` / `ragHeadersForPath` are relocated to
`src/admin/_shared/ragHttp.js` but their behavior — including the
no-retry policy, the 3000 ms / 5000 ms default timeouts, the
`{ ok, status, url, data }` envelope, and the
`AbortError → "Timeout khi gọi FastAPI RAG"` mapping — is frozen.

Admin paths still call `ragUrl()`, `ragJsonHeaders()`, and
`ragAdminJsonHeaders()` from `src/config/ragClient.js`. Header names
(`X-RAG-Internal-Key`) and the `Content-Type: application/json` rule
are unchanged.

### 4.3 Android API contract

Phase 4 touches **only** `/admin/*` and the `app.js` mount line. The
33 endpoints under `/api/**` are not modified. Specifically, no file
under `src/modules/`, `src/services/`, `src/routes/`, `src/utils.js`,
`src/auth.js`, or `src/repositories/` is edited by work items A or B.
Work items C and D add (do not modify) functions in two
repository files only.

### 4.4 DB schema & RAG service

- Schema (`backend/nodejs/database.sql`) is read-only reference. Not
  opened for writing.
- `backend/rag/**` is not touched.
- No Android source is touched.

---

## 5. Allowed files in Phase 4

### 5.1 Files you MAY EDIT

| File | Why |
| --- | --- |
| `backend/nodejs/src/admin.js` | Becomes a one-line re-export shim after work item A. |
| `backend/nodejs/src/app.js` | Add the `adminAuthMiddleware` import + insert it in `app.use("/admin", …)` (work item B). Two-line change. |
| `backend/nodejs/.env.example` is at repo root, **NOT** under `backend/nodejs/`. Edit `.env.example` at repo root only. | Append two commented documentation lines (work item B). No other line touched. |
| `backend/nodejs/src/repositories/users.repository.js` | **Only if you do work item C.** Add new functions; do not modify existing ones. |
| `backend/nodejs/src/repositories/destinations.repository.js` | **Only if you do work item D.** Add new functions; do not modify existing ones. |

Clarification on the env-example file: the file at `E:\UNUtrip\.env.example`
(repo root) is the one to append to. There is no `.env.example` under
`backend/nodejs/`.

### 5.2 Files you MAY CREATE

| File | Why |
| --- | --- |
| `backend/nodejs/src/admin/index.js` | `buildAdminRouter()` factory (work item A). |
| `backend/nodejs/src/admin/_shared/escape.js` | Shared HTML helpers (work item A). |
| `backend/nodejs/src/admin/_shared/categories.js` | Shared category helpers (work item A). |
| `backend/nodejs/src/admin/_shared/ragHttp.js` | Admin-private RAG fetch helpers (work item A). |
| `backend/nodejs/src/admin/_shared/layout.js` | Shared layout renderer (work item A). |
| `backend/nodejs/src/admin/dashboard.admin.routes.js` | Section router (work item A). |
| `backend/nodejs/src/admin/users.admin.routes.js` | Section router (work item A). |
| `backend/nodejs/src/admin/destinations.admin.routes.js` | Section router (work item A). |
| `backend/nodejs/src/admin/system.admin.routes.js` | Section router (work item A). |
| `backend/nodejs/src/admin/ragAi.admin.routes.js` | Section router (work item A). |
| `backend/nodejs/src/admin/aiReport.admin.routes.js` | Section router (work item A). |
| `backend/nodejs/src/middlewares/adminAuth.middleware.js` | HTTP Basic Auth gate (work item B). |

Total: up to twelve new files. Eleven for work item A, one for B.

### 5.3 Files you MAY READ (for context)

- `README_FIX_ALL_PHASE4.md` (this file)
- `backend/nodejs/src/admin.js` (you will be deleting most of it; read first)
- `backend/nodejs/src/app.js` (for the wire-up location)
- `backend/nodejs/src/config/ragClient.js` (to confirm helper exports)
- `backend/nodejs/src/repositories/users.repository.js` (for work item C)
- `backend/nodejs/src/repositories/destinations.repository.js` (for work item D)
- `backend/nodejs/src/routes/auth.routes.js` (as a template for the Phase 4 re-export shim)
- `.env.example` (to find the correct append point)

### 5.4 README append

You SHOULD append a `## 16. Phase 4 Result` section to
`README_FIX_ALL.md` at the repo root, mirroring the format of the
existing `## 15. Phase 3 Result` section. Keep it short: list files
changed, files created, work items completed, test results, and any
deferrals. Do NOT edit other sections of that file.

---

## 6. Forbidden files in Phase 4

Do **not** open for editing, create, or modify any of these:

- Anything under `backend/nodejs/src/modules/**` (Phase 2 module
  files — all FROZEN).
- Anything under `backend/nodejs/src/routes/**` (legacy shims +
  `routes/index.js`).
- Anything under `backend/nodejs/src/services/**` (Phase 3
  transactional services — FROZEN).
- `backend/nodejs/src/repositories/**` **except** for adding new
  (non-modifying) functions in `users.repository.js` (work item C) and
  `destinations.repository.js` (work item D). Other repository files
  remain untouched.
- `backend/nodejs/src/db.js`, `backend/nodejs/src/auth.js`,
  `backend/nodejs/src/utils.js`, `backend/nodejs/src/index.js`.
- `backend/nodejs/src/config/**`, `backend/nodejs/src/lib/**`,
  `backend/nodejs/src/schemas/**`.
- `backend/nodejs/src/shared/**` (Phase 1 + Phase 3 plumbing).
- `backend/nodejs/src/middlewares/**` **except** for creating the new
  `adminAuth.middleware.js`. Existing middleware files (`requestId`,
  `notFound`, `errorHandler`) are not modified.
- `backend/nodejs/tests/**` (Phase 5 owns testing).
- `backend/nodejs/package.json`, `backend/nodejs/package-lock.json`,
  `backend/nodejs/eslint.config.js`, `backend/nodejs/vitest.config.js`,
  `backend/nodejs/.prettierrc.json`, `backend/nodejs/database.sql`,
  `backend/nodejs/server.py`, `backend/nodejs/test_ai.js`,
  `backend/nodejs/seed.js`.
- All of `backend/rag/**` (FastAPI service).
- All Android sources (`app/**`, Gradle files, `local.properties`).
- The repo-root `.env`. Only `.env.example` may be appended to (see
  §3.2).
- The parent `README_FIX_ALL.md` **except** for appending a new
  `## 16. Phase 4 Result` section at the end.
- `backend/nodejs/src/routes.js` (the deprecated re-export shim).
- The Phase 3 plan doc `README_FIX_ALL_PHASE3.md`.
- This document `README_FIX_ALL_PHASE4.md` after Phase 4 ships.

---

## 7. Exact step-by-step plan

Recommended ordering (lowest risk first):

1. **Work item A**, in this sub-order:
   1. Create the four `_shared/` files (`escape.js`, `categories.js`,
      `ragHttp.js`, `layout.js`). Each is a verbatim move from
      `admin.js`. Do NOT yet remove the functions from `admin.js`.
      Run `npm test` and `npm run lint` — must stay green.
   2. Create one section file at a time, in the order they currently
      appear in `admin.js` (`dashboard`, then `users`, then
      `destinations`, then `system`, then `ragAi`, then `aiReport`).
      For each section: move handlers into the new file, import the
      helpers from `_shared/`, register them on the router via
      `register*AdminRoutes`, and **delete the original handlers from
      `admin.js`**. Run `npm test` after each section.
   3. After all six section files exist, write `src/admin/index.js`
      to register them all. Replace `admin.js` with the one-line
      shim. Delete the helpers from `admin.js` (they live in
      `_shared/` now). Run `npm test`, `npm run lint`, and boot the
      app to confirm the admin router still mounts.
2. **Work item B** — add `adminAuth.middleware.js`, wire it in
   `app.js`, append to `.env.example`. Run `npm test`. Verify with a
   manual `curl` that `/admin/dashboard` is still reachable when the
   env vars are unset (default-open) and blocked when they are set.
3. (Optional) **Work item C** — users admin → repository extraction.
   Run `npm test`.
4. (Optional) **Work item D** — destinations admin → repository
   extraction. Run `npm test`.
5. Append `## 16. Phase 4 Result` to `README_FIX_ALL.md`.
6. Stop. Do not start Phase 5.

After each work item, confirm the working tree is sane:

```powershell
cd E:\UNUtrip\backend\nodejs
npm test
npm run lint
```

If any test or lint check fails, stop and revert the most recent
change with `git restore <file>` and `git clean -fd backend/nodejs/src/admin/`
(do NOT commit failures).

---

## 8. Verification checklist

Run from `backend/nodejs/` unless noted.

### 8.1 Unit tests

```powershell
cd E:\UNUtrip\backend\nodejs
npm test
```

Must show:

```
Test Files  4 passed (4)
     Tests  7 passed (7)
```

These are the Phase 1/2/3 tests (`ragContract`, `ragUpstream`,
`health`, `ai-rag-chat.route`). Phase 4 does not add new tests; it
must keep all of the above passing.

### 8.2 Lint

```powershell
npm run lint
```

Must report no findings.

### 8.3 Admin smoke (highly recommended)

If MySQL is up and `.env` is configured, run:

```powershell
npm start
```

Then in another terminal:

```powershell
# Dashboard
Invoke-WebRequest -Uri http://localhost:3000/admin/dashboard -UseBasicParsing | Select-Object StatusCode

# Users API
Invoke-RestMethod -Uri http://localhost:3000/admin/users/api/1

# RAG-AI metrics proxy
Invoke-RestMethod -Uri http://localhost:3000/admin/rag-ai/ai-metrics
```

Each call should return the same status code + body shape as before
Phase 4. The HTML of `/admin/dashboard` must be byte-identical (modulo
non-deterministic data like timestamps). One quick check: pipe the
HTML through `Get-FileHash` before and after Phase 4 — only fields
that change between requests (timestamps, query duration) should
differ.

### 8.4 Admin auth smoke (work item B)

With `ADMIN_BASIC_USER` and `ADMIN_BASIC_PASS` **unset**:

```powershell
Invoke-WebRequest -Uri http://localhost:3000/admin/dashboard -UseBasicParsing
```

Should return `200`. Server log should contain a one-time
`[adminAuth] … unauthenticated (dev mode)` warning at boot.

With both env vars **set** (e.g. `ADMIN_BASIC_USER=admin`,
`ADMIN_BASIC_PASS=secret`) and the server restarted:

```powershell
# No credentials → 401 + WWW-Authenticate header
Invoke-WebRequest -Uri http://localhost:3000/admin/dashboard -UseBasicParsing -SkipHttpErrorCheck | Select-Object StatusCode, Headers

# Wrong credentials → 401
$badPair = "admin:wrong"
$badB64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($badPair))
Invoke-WebRequest -Uri http://localhost:3000/admin/dashboard -Headers @{ Authorization = "Basic $badB64" } -UseBasicParsing -SkipHttpErrorCheck | Select-Object StatusCode

# Correct credentials → 200
$okPair = "admin:secret"
$okB64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($okPair))
Invoke-WebRequest -Uri http://localhost:3000/admin/dashboard -Headers @{ Authorization = "Basic $okB64" } -UseBasicParsing | Select-Object StatusCode
```

### 8.5 File-level sanity

```powershell
# After Phase 4, admin.js is a few lines max.
(Get-Content backend\nodejs\src\admin.js | Measure-Object -Line).Lines    # expect < 20

# admin/ directory contains 11 files (6 routes + 4 shared + 1 index).
Get-ChildItem -Recurse backend\nodejs\src\admin | Where-Object { -not $_.PsIsContainer } | Measure-Object | Select-Object -Expand Count
# expect 11

# adminAuth.middleware.js exists.
Test-Path backend\nodejs\src\middlewares\adminAuth.middleware.js

# git status only shows files inside the allow-list.
git status
```

---

## 9. Pass criteria

Phase 4 is done when **ALL** of the below are true:

1. Work items A and B are implemented.
2. `npm test` shows `4 passed (4)` test files / `7 passed (7)` tests.
3. `npm run lint` is clean.
4. `git status` shows changes ONLY in the files listed in §5.1 / §5.2
   (plus the appended `## 16. Phase 4 Result` section in
   `README_FIX_ALL.md`, plus the two commented lines appended to
   `.env.example`).
5. The rendered HTML of every `/admin/*` page is byte-identical to
   pre-Phase-4 output (timestamps and live counters excepted).
6. The JSON responses of every JSON admin endpoint are byte-identical
   to pre-Phase-4 output.
7. With env vars unset, `/admin/*` is reachable (dev-mode behavior
   preserved). The one-time `[adminAuth] … unauthenticated (dev
   mode)` warning is logged once.
8. With env vars set, `/admin/*` requires HTTP Basic Auth and returns
   `401` + `WWW-Authenticate: Basic realm="UnuTrip Admin"` on
   missing/incorrect credentials.
9. `src/admin.js` is a one-line re-export shim. The original 1997
   lines are split into the new `src/admin/**` files.
10. No edits to any file listed in §6.
11. No new dependency added to `package.json`.
12. Repository public APIs are unchanged for any existing function.
    Work items C / D add new functions only; existing function
    signatures and return shapes are unchanged.

## 9.1 Fail criteria — stop immediately if any of these happen

- A test that passed before Phase 4 now fails.
- An admin endpoint returns a different status code, a different
  response shape, or different HTML than before.
- A `/admin/*` path is unreachable when env vars are unset.
- `app.use("/api", buildRouter())` is touched.
- A file listed in §6 was edited.
- A new dependency was added to `package.json`.
- HTML in any admin section file is not a byte-identical copy of the
  original.

If any of these happen, revert the offending change with
`git restore <file>` and (for newly-created files)
`git clean -fd backend/nodejs/src/admin/` then re-evaluate before
continuing.

---

## 10. Handoff prompt for the new agent

> Copy/paste exactly this into the new Cursor Agent chat. Do not abbreviate.

```
You are continuing the UnuTrip graduation-project backend refactor.

CONTEXT:
- Repo root: E:\UNUtrip.
- The Node backend lives in backend/nodejs/.
- There is a Phase 4 plan at repo root: README_FIX_ALL_PHASE4.md.
- Phase 1 (shared plumbing), Phase 2 (module shell migration for
  /api/**), and Phase 3 (AI/itinerary transactional hardening) have
  already been completed and committed. Working tree is clean.
- An Android app consumes backend/nodejs over HTTP. backend/nodejs
  proxies AI work to backend/rag. The current system works and must
  not break.
- The admin dashboard at /admin/** is server-rendered HTML and is
  currently unauthenticated. Phase 4 splits it into modules and adds
  optional HTTP Basic Auth.

TASK:
1. Read README_FIX_ALL_PHASE4.md fully. Treat it as the authoritative
   plan. You do NOT need to read README_FIX_ALL.md unless the Phase 4
   plan references a specific section of it.
2. Implement Phase 4 exactly as described:
   - Work items A and B are REQUIRED.
   - Work items C and D are OPTIONAL — only do them if A and B land
     green with the test suite still passing.
3. Touch ONLY the files listed in section 5.1 ("Allowed files: MAY
   EDIT") and at most twelve new files from section 5.2 ("MAY CREATE").
4. Do NOT touch any file listed in section 6 ("Forbidden files in
   Phase 4"), especially: modules/**, routes/**, services/**, db.js,
   auth.js, utils.js, config/**, lib/**, schemas/**, shared/**,
   existing middlewares, tests, package.json, backend/rag, Android
   sources.
5. Preserve every byte of rendered HTML, every JSON response shape,
   every URL path, every redirect target, every form field name, and
   every Vietnamese string under /admin/**. Handler bodies must be
   byte-identical copies of the originals.
6. Do not modify the database schema or any existing repository
   function. New repository functions (work items C/D) may be ADDED
   but not modified.
7. After each work item, run `npm test` AND `npm run lint` from
   backend/nodejs/. If anything regresses, revert and stop.
8. After all required work items are done, append a "Phase 4 Result"
   section to README_FIX_ALL.md (section 16). Then STOP. Do not start
   Phase 5.
9. If you encounter any ambiguity, stop and ask the user before
   writing code. Especially: if any Vietnamese string in admin HTML
   looks like it might be wrong, do NOT "fix" it — copy it verbatim.

DELIVERABLES:
- New files under backend/nodejs/src/admin/ (work item A): index.js,
  six section route files (dashboard, users, destinations, system,
  ragAi, aiReport), and four _shared/ helper files (escape,
  categories, ragHttp, layout).
- backend/nodejs/src/admin.js reduced to a one-line re-export shim
  pointing at ./admin/index.js (work item A).
- New file backend/nodejs/src/middlewares/adminAuth.middleware.js
  (work item B).
- Edit to backend/nodejs/src/app.js: add the import and insert
  adminAuthMiddleware between "/admin" and buildAdminRouter() in
  app.use(...) (work item B).
- Two commented lines appended to .env.example at the repo root
  (ADMIN_BASIC_USER, ADMIN_BASIC_PASS), placed after the existing
  RAG_ADMIN_API_KEY line (work item B).
- Optionally: new exported functions in
  backend/nodejs/src/repositories/users.repository.js and
  backend/nodejs/src/repositories/destinations.repository.js (work
  items C, D). Pilot only — do NOT refactor every admin SQL call.
- A short append to README_FIX_ALL.md describing what shipped.
- Test result + lint result + summary of changes.

Start now by reading README_FIX_ALL_PHASE4.md only, then list the
files you intend to edit and create, then proceed.
```

---

*End of `README_FIX_ALL_PHASE4.md`. After Phase 4 ships, this document
remains in the repo as historical context; it does not need to be
updated. Phase 5 will get its own handoff doc
(`README_FIX_ALL_PHASE5.md`) when the time comes.*
