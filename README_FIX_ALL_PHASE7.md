# README_FIX_ALL_PHASE7.md

> Handoff document for **Phase 7 of the UnuTrip backend refactor**.
> Audience: a fresh Cursor Agent with **no prior chat context**, implementing Phase 7 in safe, behavior-preserving steps.
> Repository root: `E:\UNUtrip` (Windows / PowerShell, also runs on POSIX).
> This file is the **single source of truth** for Phase 7. Read **`README_FIX_ALL.md`**
> **`## 18. Phase 6 Result`** first for the post–Phase 6 baseline; **`### 17.6 What is NOT done in Phase 5 (deferred)`**
> still lists several items now scoped here (templates/CSP shipped in Phase 6).

---

## 1. Mission

**Phase 7 = finish deferred *admin/data-layer* work and optional *hygiene* refactors that Phase 5–6 intentionally skipped — without breaking `/api/**`, admin JSON/HTML contracts, or Vietnamese copy.**

**Primary candidate (high value, bounded):**

1. **`POST /admin/users/save`** — move the remaining inline orchestration (`bcrypt.hashSync`, duplicate-email checks via `getUserIdByEmail` / `getUserIdByEmailExcludingUser`, `adminUpdateUser` / `createUser` branches) behind **`users.repository.js`** (or a thin `users.admin.service.js` if the team prefers a service shell) so **`users.admin.routes.js`** stays HTTP + validation + envelope only.

**Secondary candidates (explicitly optional — ship in sub-PRs only when product agrees):**

2. **Destination images from admin** — extend **`POST /admin/destinations/save`** (and possibly the destinations admin modal) to persist **`place_images`** / **`place_id_map`** where the schema already supports it; today the handler only touches **`app_places`** and the admin UI does not upload images.
3. **`routes/helpers.js` import hygiene** — repoint the eight consumer modules from the re-export shim to **`src/shared/dto/*.js`** directly (zero behavior change; import graph / churn only).
4. **CSP “phase 2”** — remove **`'unsafe-inline'`** from **`scriptSrcAttr`** by replacing **`onclick="…"`** in admin templates with **`data-*` hooks + `addEventListener`** in a small nonce-gated script or static bundle under **`public/`** (coordinate with existing **`adminTemplate.js`** / **`templates/*.html`**).

**Top-level outcomes (default minimal Phase 7):**

1. **Unchanged JSON** for all admin APIs: same `{ success, message, … }` / RAG proxy envelopes as Phase 6.
2. **Unchanged** `GET /admin/**` HTML **aside from** deliberate CSP/onclick edits if work item 4 is taken.
3. **Unchanged** every **`/api/**`** route surface consumed by Android.
4. **No schema drift** in **`database.sql`** unless the team explicitly expands scope and documents the migration.

**Non-goals (default):**

- Rewriting **`backend/rag/**`** or the Android app.
- Large **`itineraries.service.js` / `ai.routes.js`** surgery (older roadmap “Phase 3” debt) unless you spin a separate **`README_FIX_ALL_PHASE8.md`** with its own blast-radius review.
- “Nice” rewrites of Vietnamese/English user-facing strings — preserve verbatim.

---

## 2. Current state (after Phase 6, committed)

| Commit | What it did |
| --- | --- |
| `bda0e11` — **Phase 6** | Admin HTML in `src/admin/templates/`; `adminTemplate.js`; `cspNonceMiddleware`; Helmet `script-src` nonces; append **`README_FIX_ALL.md` §18**. See **`## 18. Phase 6 Result`**. |

Start Phase 7 on **`v2/database-refactor`**, **`git status` clean**, then from **`backend/nodejs/`**:

```powershell
npm test
npm run lint
```

Both green before refactor work.

### Touch map (expected)

```
backend/nodejs/src/
├── admin/users.admin.routes.js     ← POST /users/save (inline bcrypt + branches today)
├── admin/destinations.admin.routes.js  ← optional image / place_images work
├── repositories/users.repository.js    ← +admin save helpers (if work item 1)
├── repositories/destinations.repository.js  ← +image-related SQL (if work item 2)
├── routes/helpers.js              ← optional: shrink to re-export-only or delete shim later
├── shared/dto/*.js                ← optional: direct imports from consumers
└── app.js                         ← optional: script-src-attr tightening (if work item 4)
```

**Frozen unless Phase 7 adds a narrowly scoped excuse:**

- **`middlewares/adminAuth.middleware.js`** (same rule as Phase 6).
- **`admin/router` registration order** — keep **`tests/admin.router.test.js`** green (18 routes, order locked).

---

## 3. Proposed work items

Order is a **suggestion**; item **3.1** should be the default “minimal Phase 7” if you ship only one PR.

### 3.1 Work item A (recommended) — `POST /admin/users/save` → repository

**Today:** `users.admin.routes.js` contains password hashing, duplicate checks, and branching between create vs update inline.

**Target:**

- New functions on **`users.repository.js`** (names up to implementer) that encapsulate:
  - lookup by email excluding user (existing helpers already in repo),
  - transactional or sequential `UPDATE` / `INSERT` as today,
  - **callers** still use **`bcrypt.hashSync(..., 10)`** in the route **or** move hashing into a service layer — pick one; document in **`README_FIX_ALL §19`**.

**Rules:**

- Preserve every HTTP status, JSON field, and Vietnamese **`message`** string byte-for-byte unless you fix a proven bug (out of scope by default).
- Add **focused tests** only if they lock behavior (e.g. repository unit tests with mocked `db`) — do not weaken existing suites.

### 3.2 Work item B (optional) — Admin destination images

Only if the product needs parity with app **`place_images`**:

- Define multipart field names and max count **before** coding; match any existing **public API** upload patterns under **`routes/upload.js`** where possible.
- Keep **`POST /api/**`** unchanged unless Android contract work is explicitly approved.

### 3.3 Work item C (optional) — DTO import paths

- Replace `from "../routes/helpers.js"` (or equivalent) with `from "../shared/dto/....js"` in the eight consumers listed in **`README_FIX_ALL §17.6`**, then shrink or keep **`routes/helpers.js`** as a documented compatibility shim.

### 3.4 Work item D (optional) — CSP `script-src-attr` hardening

- Follow the **static bundle** or **delegated event** approach from **`README_FIX_ALL_PHASE6.md` §3.2** (second bullet).
- After removal of inline event handlers, drop **`'unsafe-inline'`** from **`scriptSrcAttr`** in **`app.js`** and verify in DevTools on **`/admin/users`**, **`/admin/destinations`**, **`/admin/rag-ai`**.

---

## 4. Default forbid-list

Unless §3 explicitly allows:

- **Do not** change **`backend/rag/**`**, Android sources, or **`database.sql`** for “drive-by” refactors.
- **Do not** churn **`src/modules/**`** or **`src/services/**`** for work that only benefits admin HTML.
- **Do not** reorder or drop admin routes covered by **`tests/admin.router.test.js`** without updating the test and documenting why.

---

## 5. Verification checklist

```powershell
cd E:\UNUtrip\backend\nodejs
npm test
npm run lint
```

- Baseline after Phase 6: **`Test Files 6 passed`** / **`Tests 17 passed`** (or higher if you add tests); regressions block merge.
- **`tests/adminAuth.middleware.test.js`** unchanged behavior (dev passthrough + gated 401 matrix).
- Manual: admin **users** create/edit/delete and **destinations** save/delete still work; if you touch uploads, exercise multipart once.

---

## 6. When Phase 7 ships

- Append **`## 19. Phase 7 Result`** to **`README_FIX_ALL.md`** (append-only; do not rewrite §1–§18).
- Keep **`README_FIX_ALL_PHASE7.md`** as historical intent; factual “what landed” belongs in **`README_FIX_ALL §19`**.

---

## 7. Handoff prompt for a new Agent

Copy/paste exactly:

```
You are continuing the UnuTrip graduation-project backend refactor.

CONTEXT:
- Repo root: E:\UNUtrip. Node backend under backend/nodejs/.
- README_FIX_ALL_PHASE7.md is authoritative for Phase 7.
- Phase 6 landed on commit bda0e11 — admin templates + CSP nonces; see README_FIX_ALL.md §18.

TASK:
1. Read README_FIX_ALL_PHASE7.md fully.
2. Default: Work item A — extract POST /admin/users/save persistence into users.repository.js (or thin service) with identical JSON/Vietnamese messages.
3. Optional B/C/D only if explicitly in scope — images, DTO imports, CSP script-src-attr.
4. npm test && npm run lint after each coherent step; keep tests/admin.router.test.js and adminAuth tests green.
5. Append "## 19. Phase 7 Result" to README_FIX_ALL.md when done.

DELIVERABLES:
- Cleaner admin user-save layering; optional items documented in §19.
```

---

*End of `README_FIX_ALL_PHASE7.md`. Larger “Phase 3 debt” (itineraries transactions, `ai.routes.js` inline SQL, etc.) should get its own phase doc when scoped.*
