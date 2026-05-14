# README_FIX_ALL_PHASE6.md

> Handoff document for **Phase 6 of the UnuTrip backend refactor**.
> Audience: a fresh Cursor Agent with **no prior chat context**, implementing Phase 6 in safe, behavior-preserving steps.
> Repository root: `E:\UNUtrip` (Windows / PowerShell, also runs on POSIX).
> This file is the **single source of truth** for Phase 6. Treat `README_FIX_ALL.md`
> as background only — for deferrals after Phase 5, read **`## 17. Phase 5 Result`**
> and **`### 17.6 What is NOT done in Phase 5 (deferred)`** there first.

---

## 1. Mission

**Phase 6 = extract admin HTML from inline JS template literals → then tighten Helmet CSP, without breaking any URL/HTML/JSON/Vietnamese copy contract.**

After Phase 5, admin markup still lives inside **large template literals** in
`backend/nodejs/src/admin/*.admin.routes.js`, and the chrome layout lives in
`backend/nodejs/src/admin/_shared/layout.js` (`renderLayout`). Express `app.js` still configures Helmet CSP with **`'unsafe-inline'`** on **`scriptSrc`** and **`scriptSrcAttr`**, plus Tailwind CDN, Font CDN, Google Fonts — that was intentional for the demo shell; Phase 6 is allowed to rework CSP **after** inline scripts/styles are eliminated or replaced (nonces/hashes/external bundles).

**Top-level outcomes:**

1. **Byte-identical rendered HTML** for every **`GET /admin/**` that returns HTML** (except known non-determinism already called out in prior phases — e.g. date formatting counters).
2. **Unchanged JSON** for admin APIs (`GET /users/api/:id`, `GET /destinations/api/:id`,
   `GET /ai-report`, `/rag-ai/*` proxies): same envelopes and field names as Phase 5.
3. **Unchanged URLs**, redirects, form field names, and HTTP statuses under `/admin/**`.
4. **Do not modify** **`/api/**`**, **`backend/rag/**`**, Android, or **`database.sql`** schema in the default Phase 6 scope unless a follow-up mini-plan explicitly expands scope.

**Non-goals (default):**

- "Fixing" Vietnamese copy or English messages — transcribe verbatim.
- Rewriting admin as a SPA in another codebase or swapping Express for another runtime.
- Adding dependencies without an explicit justification in the Phase 6 PR/handoff appendix.
- Infra/deploy/Gradle changes — optional only if the team expands scope later.

---

## 2. Current state (after Phase 5, committed)

| Commit | What it did |
| --- | --- |
| `3768fb2` — **Phase 5** | Split `routes/helpers.js` → `src/shared/dto/{user,destination,itinerary}Dto.js`; `adminAuth` + admin router Vitest suites; remainder of pilot admin SQL extracted to repos (see **`README_FIX_ALL.md §17`**). |

Start Phase 6 on **`v2/database-refactor`**, **`git status` clean**, then from `backend/nodejs/` run **`npm test`** and **`npm run lint`** — both green before refactoring.

### Touch map

```
backend/nodejs/src/
├── app.js                         ← HELMET CSP (unsafe-inline scripts / scriptSrcAttr today)
├── admin/*admin.routes.js         ← inline HTML templates in GET handlers
├── admin/_shared/layout.js       ← outer shell (<html>, CDN links)
└── middlewares/adminAuth.middleware.js ← prefer frozen unless Phase 6 adds a narrowly scoped auth work item
```

**CSP reality check:** Removing `'unsafe-inline'` without breaking **`https://cdn.tailwindcss.com`**, CDN fonts/icons, or existing inline `<script>` blocks requires either **nonces per response**, **static bundled admin JS/CSS**, **hashed inline**, or dropping/replacing those CDNs deliberately. Smoke-test **`/admin/dashboard`** and **users / destinations** (modals + `fetch`) in DevTools after every CSP tightening step.

---

## 3. Proposed work items

Order matters: **templates first**, **CSP second**. Split across multiple PRs if review risk is high.

### 3.1 Work item A — extract admin templates out of literals

**Today:** each section file concatenates escaped dynamic fields into enormous template strings; `renderLayout(content, …)` wraps the CDN shell.

**Approach:**

1. Introduce one canonical directory for admin fragments (pick **one** name in the Phase 6 PR — e.g. `src/admin/templates/` **or** `views/admin/` under `nodejs/` — do not duplicate two parallel conventions).

2. Load fragments with **`fs`** (sync or tiny async loader) plus a **minimal, auditable substitution** mechanism (named placeholders). Avoid heavyweight template engines unless the team commits to a dependency bump with rationale.

3. **Byte-parity gate:** snapshot or deterministic diff of each HTML `GET` response against Phase 5 output (pick one methodology in the Phase 6 PR document it in **`README_FIX_ALL §18`**).

4. Preserve **admin router registration order** (`18` routes) enforced by **`tests/admin.router.test.js`**.

### 3.2 Work item B — tighten Helmet CSP (after A)

Baseline block in `backend/nodejs/src/app.js`:

```26:46:backend/nodejs/src/app.js
  app.use(
    helmet({
      crossOriginResourcePolicy: { policy: "cross-origin" },
      contentSecurityPolicy: {
        directives: {
          defaultSrc: ["'self'"],
          scriptSrc: ["'self'", "'unsafe-inline'", "https://cdn.tailwindcss.com"],
          scriptSrcAttr: ["'unsafe-inline'"],
          styleSrc: [
            "'self'",
            "'unsafe-inline'",
            "https://cdnjs.cloudflare.com",
            "https://fonts.googleapis.com",
          ],
          fontSrc: ["'self'", "https://cdnjs.cloudflare.com", "https://fonts.gstatic.com", "data:"],
          imgSrc: ["'self'", "data:", "https:", "http:"],
          connectSrc: ["'self'", "http:", "https:"],
        },
      },
    })
  );
```

**Pick one CSP strategy once A is landed:**

- **Nonces:** middleware sets `res.locals.cspNonce`, inject into `<script nonce=…>` and Helmet `'nonce-{value}'`; remove broad `'unsafe-inline'` where possible.
- **Static admin bundle:** compile admin JS/CSS under `public/` served as `'self'`, replace `onclick=` with `addEventListener` — only then tighten **`scriptSrcAttr`**.

Requirements:

- `npm test` + `npm run lint` green after **each incremental CSP edit**.
- Manual smoke: dev-mode **`adminAuth`** (env unset passthrough + warn-once + gated mode 401 matrix) unchanged in behavior (`tests/adminAuth.middleware.test.js` must remain green unchanged).

---

## 4. Optional backlog — Phase 6 *or later* (explicitly deferrable)

Items below are called out in **`README_FIX_ALL.md §17.6`**; they are **not** required minimal Phase 6. If tackled, isolate in a clearly labeled sub-PR:

- **`POST /users/save`** repository extraction (`bcrypt` + INSERT/UPDATE + duplicate-email lookups) — may slide to Phase 7.
- **Image upload + `place_images` / `place_id_map`** for destinations save — admin UI currently does not implement uploads; ship only when product asks.

---

## 5. Default forbid-list

Unless §3 explicitly allows:

- **Do not** churn `backend/nodejs/src/modules/**` or `backend/nodejs/src/services/**` for admin cosmetic refactors alone.
- **Do not** modify `routes/helpers.js` or `shared/dto/**` (Phase 5 territory) except for unblockers documented in Phase 6 §18 Result.
- **Do not** touch `backend/rag/**`, Android, or DB schema edits in **`database.sql`**.

---

## 6. Verification checklist

```powershell
cd E:\UNUtrip\backend\nodejs
npm test
npm run lint
```

Expected baseline after Phase 5: **`Test Files 6 passed`** / **`Tests 17 passed`** (or higher if new tests landed); regressions unacceptable.

Manual (after template + CSP edits):

- Admin pages render; modals (`users`, `destinations`) fetch/save/delete paths still behave.
- **No surprise CSP breakage** — fix violations before declaring Phase 6 done.

---

## 7. When Phase 6 ships

- Append **`## 18. Phase 6 Result`** to **`README_FIX_ALL.md`** (append-only; don’t rewrite prior sections).
- Keep **`README_FIX_ALL_PHASE6.md`** as historical intent; factual “what landed” belongs in **`README_FIX_ALL §18`**.

---

## 8. Handoff prompt for a new Agent

Copy/paste exactly:

```
You are continuing the UnuTrip graduation-project backend refactor.

CONTEXT:
- Repo root: E:\UNUtrip. Node backend under backend/nodejs/.
- README_FIX_ALL_PHASE6.md is authoritative for Phase 6.
- Phase 5 landed on commit 3768fb2 — DTO split, admin SQL repo sweep continuation,
  adminAuth + admin router tests — see README_FIX_ALL.md §17.

TASK:
1. Read README_FIX_ALL_PHASE6.md fully.
2. Work item A: extract admin HTML from inline literals into discrete template files /
   a small loader layer; preserve GET HTML byte-identical to Phase 5 (except known nondeterminism).
3. Work item B: tighten helmet CSP only after unsafe-inline reliance is eliminated or fenced with nonces.
4. npm test && npm run lint from backend/nodejs/ after each coherent step — stop on red.
5. Append "## 18. Phase 6 Result" to README_FIX_ALL.md documenting files changed/made, CSP strategy chosen, screenshots or snapshot notes optional.
6. Do not tackle Android API, rag service, modules/services churn, or schema without explicit scope bump.

DELIVERABLES:
- Cleaner admin template wiring + safer CSP posture.
- Green tests/lint §6 baseline.
```

---

*End of `README_FIX_ALL_PHASE6.md`. Plan Phase 7 (e.g. users-save repo extraction / image uploads) in a future `README_FIX_ALL_PHASE7.md` when scoped.*
