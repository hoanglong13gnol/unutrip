# README_FIX_ALL_PHASE3.md

> Handoff document for **Phase 3 of the UnuTrip backend refactor**.
> Audience: a fresh Cursor Agent that has **no prior chat context** and must
> implement Phase 3 in safe, behavior-preserving steps.
> Repository root: `E:\UNUtrip` (Windows / PowerShell, also runs on POSIX).
> This document is the **single source of truth** for Phase 3. The parent
> document `README_FIX_ALL.md` is informational context only; you do **not**
> need to open it to do Phase 3 — everything you need is here.

---

## 1. Mission

**Phase 3 = AI / itinerary transactional hardening.**

Make the AI itinerary persistence flows safe under partial failure, by:

1. Moving the embedded raw-SQL transaction in
   `src/modules/ai/ai.controller.js#suggestItinerary` out of the controller
   and into a service function that uses the Phase-1 `withTransaction`
   helper.
2. Wrapping the two non-transactional flows
   `itinerariesService.createItineraryFromAiOption` and
   `itinerariesService.createItineraryFromAiSelection` in a single
   `withTransaction` boundary so a mid-flight failure cannot leave partial
   itineraries in the DB.
3. Removing the `console.log(JSON.stringify(req.body)...)` call in the
   `POST /api/itineraries/save-ai` controller (PII risk).
4. (Optional, only if time permits and tests pass) refactoring the existing
   manual `conn.beginTransaction()` block in
   `itinerariesService.saveAiItinerary` to use `withTransaction` for
   consistency.
5. (Optional, only if all of 1–4 are green) extracting the duplicated
   `timeSlots` array used by both AI itinerary-creation flows into a small
   shared helper.

**Goal:** preserve every byte of the Android API contract and the RAG
contract while making these four flows atomic and quiet.

**Non-goals (forbidden in Phase 3):**

- **Do not** change the Android-facing API contract under `/api/**`.
- **Do not** change the RAG upstream contract.
- **Do not** modify the database schema.
- **Do not** touch `backend/rag/**` (FastAPI service).
- **Do not** touch any Android source (`app/`, Gradle files, etc.).
- **Do not** add new dependencies.
- **Do not** edit `package.json`, `package-lock.json`, `database.sql`, `.env`,
  `.env.example`, `eslint.config.js`, `vitest.config.js`, or any
  `.prettierrc.json`.

---

## 2. Current state (after Phase 1 + Phase 2, already committed)

Two prior commits land before Phase 3:

| Commit | What it did |
| --- | --- |
| `c8bade9` — **Phase 1** | Added shared kit: `HttpError`, `asyncHandler`, `apiOk/apiFail/apiList`, `withTransaction`, plus `requestId` / `notFound` / `errorHandler` middlewares wired into `app.js`. `utils.js` re-exports `apiOk`/`apiFail` from `shared/http/response.js` for backward compatibility. `errorHandlerMiddleware` only logs 5xx (a refinement landed in Phase 2). |
| `2057944` — **Phase 2** | Moved all 8 feature routes from `src/routes/*.routes.js` into `src/modules/<feature>/{routes,controller}.js`. The old `routes/*.routes.js` files are now one-line re-export shims. `routes/index.js` imports `register*Routes` from the new module paths. Handlers are byte-identical copies of the originals (same validation, same response shapes, same status codes, same Vietnamese strings) — only their location changed. **The embedded raw-SQL transaction from `routes/ai.routes.js#suggestItinerary` was moved verbatim into `src/modules/ai/ai.controller.js#suggestItinerary` without any transactional refactor** — that is what Phase 3 must fix. |

You should start Phase 3 with a **clean working tree** on branch
`v2/database-refactor`. Verify with `git status` before starting.

### Layer map (as of start of Phase 3)

```
backend/nodejs/src/
├── app.js                              Express factory (Phase 1 wiring)
├── index.js                            HTTP listener
├── routes.js                           one-line re-export of ./routes/index.js (legacy)
├── routes/
│   ├── index.js                        builds Express router from modules/
│   ├── helpers.js                      DTO mappers, domain helpers (FROZEN)
│   ├── upload.js                       multer factory (FROZEN)
│   └── *.routes.js                     one-line shims pointing at modules/ (FROZEN)
├── modules/
│   ├── ai/
│   │   ├── ai.routes.js                paths/methods only
│   │   └── ai.controller.js            << Phase 3 must trim suggestItinerary here
│   ├── itineraries/
│   │   ├── itineraries.routes.js
│   │   └── itineraries.controller.js   << Phase 3 must remove console.log(req.body) in saveAiItinerary
│   ├── auth/, users/, favorites/, destinations/, reviews/, health/
│   └── (controllers contain verbatim Phase-2 logic — DO NOT TOUCH)
├── services/
│   ├── ai.service.js                   << Phase 3 may add ONE new function here
│   ├── itineraries.service.js          << Phase 3 must edit createItineraryFromAiOption / createItineraryFromAiSelection
│   ├── favorites.service.js            FROZEN
│   ├── destinations.service.js         FROZEN
│   └── reviews.service.js              FROZEN
├── repositories/
│   ├── itineraries.repository.js       FROZEN — already supports (payload, conn) overload
│   ├── placeIdMap.repository.js        FROZEN
│   └── *.repository.js                 FROZEN
├── shared/
│   ├── http/                           HttpError.js, asyncHandler.js, response.js (Phase 1, FROZEN)
│   └── db/
│       └── withTransaction.js          Phase 1 helper — Phase 3 wires this in
├── middlewares/                        Phase 1 middlewares (FROZEN)
├── config/, lib/, schemas/, auth.js, db.js, utils.js, admin.js  ALL FROZEN
└── seed.js, data/                      FROZEN
```

---

## 3. What Phase 3 must do — the four work items

### 3.1 Work item A (REQUIRED) — relocate `suggestItinerary` transaction

**Symptom.** `src/modules/ai/ai.controller.js#suggestItinerary` currently
contains ~60 lines of raw SQL inside the controller (lines ~50–116 of that
file as of `2057944`):

```js
const conn = await db.pool.getConnection();
try {
  await conn.beginTransaction();
  const [itinRes] = await conn.execute(`INSERT INTO itineraries ...`, [...]);
  const itineraryId = itinRes.insertId;
  if (aiResult.days && Array.isArray(aiResult.days)) {
    for (const day of aiResult.days) {
      const [dayRes] = await conn.execute(`INSERT INTO itinerary_days ...`, [...]);
      const dayId = dayRes.insertId;
      if (day.items && Array.isArray(day.items)) {
        for (const item of day.items) {
          await conn.execute(`INSERT INTO itinerary_items ...`, [...]);
        }
      }
    }
  }
  await conn.commit();
  // build newItin response object …
} catch (err) {
  await conn.rollback();
  throw err;
} finally {
  conn.release();
}
```

**Required Phase-3 change.**

1. Add ONE new service function. Choose location:
   - **Preferred:** `src/services/itineraries.service.js` →
     `export async function persistAiSuggestedItinerary({ userId, aiResult, isoStart, isoEnd, totalDays, budget })`.
   - It must do the same INSERTs but via:
     - `withTransaction` from `src/shared/db/withTransaction.js`.
     - The existing repository functions (already support `(payload, conn)`):
       - `itinerariesRepository.insertItinerary(payload, conn)`
       - `itinerariesRepository.insertItineraryDay(payload, conn)`
       - `itinerariesRepository.insertItineraryItem(payload, conn)`
   - Defaults must be preserved byte-for-byte:
     - `title || "Lịch trình AI tạo"`
     - `description || "Tạo bởi Hướng dẫn viên du lịch ảo."`
     - `status` literal `'planned'` (already in the repository SQL).
     - `estimatedBudget`: `budget || null`.
     - For each AI day: `day.dayNumber || 1`, computed `dayDateStr` = startDate + (dayNumber-1) days, formatted via `toIsoDate(date.toISOString().split("T")[0])`.
     - For each item: default `startTime` `"08:00"`, `endTime` `"09:00"`, `note` `""`, `orderIndex` starts at `0` and increments.
   - Return shape:
     ```
     {
       id, userId, title, description, startDate, endDate, totalDays,
       status: "planned", estimatedBudget
     }
     ```
     i.e. exactly the `newItin` object the old controller built.

2. Replace the inline transaction block in
   `src/modules/ai/ai.controller.js#suggestItinerary` with a single call:
   ```js
   const newItin = await itinerariesService.persistAiSuggestedItinerary({
     userId: req.user.userId,
     aiResult,
     isoStart,
     isoEnd,
     totalDays,
     budget
   });
   return res.json({
     success: true,
     itinerary: newItin,
     message: "Đã tạo lịch trình bằng AI thành công!"
   });
   ```
3. Remove the `import { db } from "../../db.js";` line from
   `ai.controller.js` (no longer needed after this change). All other
   imports stay.
4. **Outer error handling unchanged.** The existing `try { … } catch (error) { res.status(500).json({ success:false, message:"Lỗi tạo lịch trình tự động: " + error.message }) }` around the whole handler must stay. Service throws ⇒ outer catch wraps the message just like before.

**Forbidden in work item A.**

- Do not change the SQL statements themselves (the repositories already
  hold the canonical SQL).
- Do not rename `lastInsertRowid`.
- Do not change `'planned'` to anything else.
- Do not change the default times or default note string.
- Do not change the response body shape: must remain
  `{ success:true, itinerary: <newItin>, message: "Đã tạo lịch trình bằng AI thành công!" }`.
- Do not move `daysBetweenInclusive` / `toIsoDate` computation out of the
  controller — Phase 3 only relocates the persistence half. Date parsing
  remains in the controller.
- Do not change the `invalid_ai_json` error path (the
  `genResult.reason === "invalid_ai_json"` branch returns a 500 with
  `"AI trả về dữ liệu không hợp lệ."`).

---

### 3.2 Work item B (REQUIRED) — wrap `createItineraryFromAiOption` in `withTransaction`

**Symptom.** `src/services/itineraries.service.js#createItineraryFromAiOption`
performs ~10+ raw `db.run(...)` INSERTs into `itineraries`, `itinerary_days`,
and `itinerary_items` **without** a transaction (see lines ~309–423 of that
file as of `2057944`). A failure half-way leaves orphan rows.

**Required Phase-3 change.**

1. Keep ALL pre-flight validation logic exactly as-is (input flattening,
   `resolveDestinationIdsFromSelection`, `placeIdMapRepository.getDestinationIdByRagPlaceId`
   lookups, the early returns
   `{ ok:false, reason:"no_mapped_destinations", … }` and
   `{ ok:false, reason:"invalid_dates" }`, the `totalDays` computation,
   the `finalBudget` and `destinationIdByRawPlaceId` maps, the `timeSlots`
   array).
2. From the first INSERT onward, run **everything** inside a single
   `withTransaction(async (conn) => { … })` block:
   - Replace the raw `db.run("INSERT INTO itineraries …")` with
     `itinerariesRepository.insertItinerary({…}, conn)`. The repository’s
     `(payload, conn)` overload is already implemented.
   - Replace each raw `db.run("INSERT INTO itinerary_days …")` with
     `itinerariesRepository.insertItineraryDay({…}, conn)`.
   - Replace each raw `db.run("INSERT INTO itinerary_items …")` with
     `itinerariesRepository.insertItineraryItem({…}, conn)`. Note this
     repository function currently returns `void`; that is fine — the
     existing service code does not use the return value.
3. The shape of arguments passed to each repository call must match the
   raw SQL columns exactly:
   - `insertItinerary({ userId, title, description: description ?? null, startDate, endDate, totalDays, estimatedBudget: finalBudget }, conn)` —
     **note `description ?? null` to preserve the current `description ?? null` behavior.**
   - `insertItineraryDay({ itineraryId, dayNumber, date: dateText }, conn)`.
   - `insertItineraryItem({ dayId, destinationId, startTime: item?.startTime || slot[0], endTime: item?.endTime || slot[1], note: item?.reason || "Được chọn từ AI tour", orderIndex: index + 1 }, conn)` —
     **note `orderIndex: index + 1` (not `index`) and `note: item?.reason || "Được chọn từ AI tour"` (NOT a translated string)** — these are the existing values.
4. Return value of the service function must remain bit-identical:
   ```js
   return {
     ok: true,
     data: {
       id: itineraryId,
       itineraryId,
       optionId: optionId ?? null,
       selectedCount: insertedCount,
       unresolved
     }
   };
   ```
5. Wrap so the `return` value of `withTransaction(async (conn) => { … })`
   becomes the new function’s return value. Compute `itineraryId` and
   `insertedCount` inside the callback and return them as
   `{ itineraryId, insertedCount }`; outside the callback assemble the
   final `{ ok:true, data:{ … } }` (or do it all inside).
6. **Do not move pre-validation inside the transaction.** Specifically,
   the `selectedDestinations` flattening, the place-id-map lookups, the
   `no_mapped_destinations` / `invalid_dates` early returns, and the
   `totalDays` / `finalBudget` / `destinationIdByRawPlaceId` setup all
   stay above the `withTransaction(...)` call. Only the INSERTs run inside.

**Forbidden in work item B.**

- Do not change SQL strings inside the repository functions.
- Do not modify the repository functions at all.
- Do not change the return-on-failure shapes (callers in the controller
  match on `reason === "no_mapped_destinations"` and `reason === "invalid_dates"`).
- Do not change the `"Được chọn từ AI tour"` note string.
- Do not change `index + 1` to `index` for `orderIndex`.
- Do not change `timeSlots[index % timeSlots.length]`.

---

### 3.3 Work item C (REQUIRED) — wrap `createItineraryFromAiSelection` in `withTransaction`

Same pattern as work item B, applied to
`src/services/itineraries.service.js#createItineraryFromAiSelection` (lines
~464–578 of that file as of `2057944`).

**Required Phase-3 change.**

1. Keep ALL pre-flight validation logic as-is: the
   `selectedDestinationIds` vs `selectedDestinations` fallback, the
   `resolveDestinationIdsFromSelection` call (when applicable), the
   `no_mapped_destinations` / `invalid_dates` early returns, and the
   `totalDays` / `finalBudget` setup.
2. From the first INSERT onward, run everything inside a single
   `withTransaction(async (conn) => { … })` block, swapping all raw
   `db.run(...)` calls for repository functions with `conn`:
   - `itinerariesRepository.insertItinerary({ userId, title, description: description ?? null, startDate, endDate, totalDays, estimatedBudget: finalBudget }, conn)`.
   - For each `dayNumber` 1..`totalDays`:
     `itinerariesRepository.insertItineraryDay({ itineraryId, dayNumber, date: dateText }, conn)`. Collect the returned `lastInsertRowid` into the existing `dayIds` array (preserve order).
   - For each destination at index `i`:
     `itinerariesRepository.insertItineraryItem({ dayId: dayIds[dayIndex], destinationId: destinationIds[i], startTime: slot[0], endTime: slot[1], note: "Được chọn từ AI gợi ý", orderIndex: orderIndex + 1 }, conn)`. **Note `"Được chọn từ AI gợi ý"` (different from work item B), and `orderIndex + 1`** — these are the existing values.
3. Return shape must remain bit-identical:
   ```js
   return {
     ok: true,
     data: {
       id: itineraryId,
       itineraryId,
       selectedCount: destinationIds.length,
       destinationIds,
       unresolved
     }
   };
   ```

**Forbidden in work item C.**

- Same constraints as work item B.
- Do not change the `"Được chọn từ AI gợi ý"` note string (different from
  the option flow’s `"Được chọn từ AI tour"`).
- Do not change the `dayIndex = i % totalDays` / `orderIndex = Math.floor(i / totalDays)` distribution math.

---

### 3.4 Work item D (REQUIRED) — drop `console.log(req.body)` in `saveAiItinerary`

**Symptom.**
`src/modules/itineraries/itineraries.controller.js#saveAiItinerary` opens
with:

```js
console.log("[AI] Save AI Itinerary Request:", JSON.stringify(req.body).substring(0, 500));
```

That logs up to 500 chars of arbitrary user payload (PII risk).

**Required Phase-3 change.** Remove that single `console.log` line. Keep
everything else in the handler exactly as-is, including the
`try { … } catch (error) { console.error("Save AI Itinerary Error:", error); … }` block (the `console.error` on failure stays — it logs the error message, not user data).

**Forbidden in work item D.**

- Do not change the response on success
  (`{ success:true, message:"Đã lưu lịch trình thành công!" }`).
- Do not change the failure path
  (`res.status(500).json({ success:false, message:"Lỗi lưu DB: " + detail })`).
- Do not remove the `console.error("Save AI Itinerary Error:", error)` —
  that log is operator-facing, not PII.

---

### 3.5 Work item E (OPTIONAL — only if A–D land green) — adopt `withTransaction` in `saveAiItinerary` service

`src/services/itineraries.service.js#saveAiItinerary` currently opens a
connection manually (`db.pool.getConnection()` + `beginTransaction` +
`commit` / `rollback` / `release`). It IS transactional, so this is a
**consistency** refactor, not a bug fix.

If you take this on:

- Replace the manual conn dance with a single
  `await withTransaction(async (conn) => { … })`.
- Move the INSERT loop inside the callback.
- Keep the `(payload, conn)` calls into the repository functions exactly
  as they are now.
- Do not change behavior: same SQL, same defaults
  (`title || "Lịch trình AI"`, `description || "Đã lưu từ gợi ý AI."`,
  `estimatedBudget: budget || null`, item defaults `"08:00"` / `"09:00"` /
  `""`, `orderIndex` increments from `0`).
- Do not change the `safeStartDate` / `safeEndDate` / `totalDays` /
  `isoStart` / `isoEnd` derivation above the transaction.

Skip work item E if you have any doubt. The current code already commits
or rolls back correctly.

---

### 3.6 Work item F (OPTIONAL — only if A–E land green) — extract shared `timeSlots` constant

Both `createItineraryFromAiOption` and `createItineraryFromAiSelection`
contain the same array:

```js
const timeSlots = [
  ["08:00", "10:00"],
  ["10:30", "12:00"],
  ["14:00", "16:00"],
  ["16:30", "18:00"]
];
```

If you take this on:

- Create `src/shared/utils/timeSlots.js`:
  ```js
  export const DEFAULT_AI_ITINERARY_TIME_SLOTS = [
    ["08:00", "10:00"],
    ["10:30", "12:00"],
    ["14:00", "16:00"],
    ["16:30", "18:00"]
  ];
  ```
- Import the constant in both service functions, replace the local
  array. Do not change values, order, count, or formatting of the
  strings.
- This is the **only** new file Phase 3 is allowed to create. (Plus the
  optional one in §3.7 if you do it.)

Skip work item F if A–E took a while. Duplication is harmless.

---

## 4. Frozen contracts — do not violate

### 4.1 Android API contract (33 endpoints under `/api/**`)

Every path, request body field name, response body field name, and HTTP
status code must remain identical. The endpoints touched indirectly by
Phase 3 work items are:

| Method | Path | Response on success |
| --- | --- | --- |
| POST | `/api/ai/suggest-itinerary` | `200 { success:true, itinerary:{ id, userId, title, description, startDate, endDate, totalDays, status:"planned", estimatedBudget }, message:"Đã tạo lịch trình bằng AI thành công!" }` |
| POST | `/api/itineraries/save-ai` | `200 { success:true, message:"Đã lưu lịch trình thành công!" }` |
| POST | `/api/itineraries/create-from-option` | `200 { success:true, message:"Tạo lịch trình từ tour AI thành công", data:{ id, itineraryId, optionId, selectedCount, unresolved } }` or `400` with `data.unresolved` (`reason === "no_mapped_destinations"`) or `400 { ... message:"Ngày đi/ngày về không hợp lệ", data:null }` |
| POST | `/api/itineraries/create-from-selection` | `200 { success:true, message:"Tạo lịch trình từ AI gợi ý thành công", data:{ id, itineraryId, selectedCount, destinationIds, unresolved } }` or `400` with `data.{ receivedSelectedDestinations, receivedSelectedDestinationIds, unresolved }` or `400 { ... message:"Ngày đi/ngày về không hợp lệ", data:null }` |

Failure envelopes from the controllers (4xx/5xx) are also frozen — see
the existing `ai.controller.js` for the exact strings.

### 4.2 RAG contract

The four work items do **not** touch RAG at all. Leave
`src/lib/ragUpstream.js`, `src/config/ragClient.js`, `src/schemas/ragContract.js`,
`src/services/ai.service.js`’s RAG-facing functions (`requestItineraryPreview`,
`requestItineraryOptions`, `requestRagChatSimple`, `requestRagChatFallbackForAiChat`,
`generateSuggestItineraryAiResult`), and everything under `backend/rag/**`
untouched.

You may **add** one new function to `src/services/ai.service.js` OR to
`src/services/itineraries.service.js` (see §3.1). You may not edit the
existing RAG-facing functions.

### 4.3 DB schema & repositories

- The schema (`backend/nodejs/database.sql`) is read-only reference. Do not
  modify or open for writing.
- The repository public APIs (function names, parameter shapes, return
  shapes) are frozen.
- `itinerariesRepository.insertItinerary`, `insertItineraryDay`, and
  `insertItineraryItem` already support a second `(payload, conn)`
  parameter for transactional inserts. Use that overload — do not add a
  new overload.
- `db.run` results carry `lastInsertRowid`. Do not rename.
- `db.pool.getConnection()` may be called only by `withTransaction.js`; do
  not call it directly anywhere else in Phase 3.

---

## 5. Allowed files in Phase 3

### 5.1 Files you MAY EDIT

| File | Why |
| --- | --- |
| `backend/nodejs/src/modules/ai/ai.controller.js` | Trim the embedded transaction in `suggestItinerary` (work item A). Drop the now-unused `import { db } …` line. |
| `backend/nodejs/src/modules/itineraries/itineraries.controller.js` | Remove the single `console.log(req.body)` in `saveAiItinerary` (work item D). |
| `backend/nodejs/src/services/itineraries.service.js` | Wrap `createItineraryFromAiOption` and `createItineraryFromAiSelection` in `withTransaction` (work items B, C). Optionally refactor `saveAiItinerary` to use `withTransaction` (work item E). Optionally add `persistAiSuggestedItinerary` here (work item A). |
| `backend/nodejs/src/services/ai.service.js` | **Alternative** location for `persistAiSuggestedItinerary` (work item A). Either this file OR `itineraries.service.js` — pick one. Do not edit any existing function in this file. |

### 5.2 Files you MAY CREATE

| File | Why |
| --- | --- |
| `backend/nodejs/src/shared/utils/timeSlots.js` | Only if you do work item F. Tiny constant module. |

### 5.3 Files you MAY READ (for context)

- `README_FIX_ALL_PHASE3.md` (this file)
- `backend/nodejs/src/shared/db/withTransaction.js` (the helper you’ll use)
- `backend/nodejs/src/repositories/itineraries.repository.js` (to confirm `(payload, conn)` shape)
- `backend/nodejs/src/repositories/placeIdMap.repository.js` (referenced by the two service flows; do not edit)
- `backend/nodejs/src/utils.js` (uses `daysBetweenInclusive`, `toIsoDate`)
- `backend/nodejs/src/modules/ai/ai.routes.js` (no edit; just to confirm routes still mount)

### 5.4 README append

You SHOULD append a `Phase 3 Result` section to `README_FIX_ALL.md` at the
repo root, mirroring the format of the existing `## 14. Phase 2 Result`
section. Keep it short: list files changed, work items completed, test
results. Do NOT edit other sections of that file.

---

## 6. Forbidden files in Phase 3

Do **not** open for editing, create, or modify any of these:

- Anything under `backend/nodejs/src/modules/` except the two files listed
  in §5.1 (`ai/ai.controller.js`, `itineraries/itineraries.controller.js`).
  In particular, do **not** touch:
  - `modules/auth/**`, `modules/users/**`, `modules/favorites/**`,
    `modules/destinations/**`, `modules/reviews/**`, `modules/health/**`.
  - `modules/ai/ai.routes.js`, `modules/itineraries/itineraries.routes.js`.
- `backend/nodejs/src/routes/**` (the legacy shims and `routes/index.js`).
- `backend/nodejs/src/repositories/**` (all repositories — they already
  support `conn`; just use the overload).
- `backend/nodejs/src/services/favorites.service.js`,
  `services/destinations.service.js`, `services/reviews.service.js`.
- `backend/nodejs/src/admin.js`, `backend/nodejs/src/db.js`,
  `backend/nodejs/src/auth.js`, `backend/nodejs/src/utils.js`.
- `backend/nodejs/src/config/**`, `backend/nodejs/src/lib/**`,
  `backend/nodejs/src/schemas/**`.
- `backend/nodejs/src/shared/http/**`,
  `backend/nodejs/src/shared/db/withTransaction.js` (already correct from Phase 1 — **import it, do not edit it**).
- `backend/nodejs/src/middlewares/**`, `backend/nodejs/src/app.js`,
  `backend/nodejs/src/index.js`.
- `backend/nodejs/tests/**` (do not add or modify tests in Phase 3 — Phase 5 owns testing).
- `backend/nodejs/package.json`, `backend/nodejs/package-lock.json`,
  `backend/nodejs/eslint.config.js`, `backend/nodejs/vitest.config.js`,
  `backend/nodejs/.prettierrc.json`, `backend/nodejs/database.sql`,
  `backend/nodejs/server.py`, `backend/nodejs/test_ai.js`,
  `backend/nodejs/seed.js`.
- All of `backend/rag/**` (FastAPI service).
- All Android sources (`app/**`, Gradle files, `local.properties`).
- The repo-root `.env`, `.env.example`, and the parent
  `README_FIX_ALL.md` **except** for appending a new `## 15. Phase 3 Result`
  section at the end.

---

## 7. Exact step-by-step plan

Recommended ordering (lowest risk first):

1. **Work item D** (drop one `console.log`). Run `npm test` — must stay green.
2. **Work item B** (`createItineraryFromAiOption` → `withTransaction`).
   Run `npm test` — must stay green.
3. **Work item C** (`createItineraryFromAiSelection` → `withTransaction`).
   Run `npm test`.
4. **Work item A** (move `suggestItinerary` transaction into service).
   Run `npm test`. This is the biggest change; do it after the others so
   any regression is easier to isolate.
5. (Optional) **Work item E** (refactor `saveAiItinerary` service to use
   `withTransaction`). Run `npm test`.
6. (Optional) **Work item F** (extract `timeSlots` constant). Run `npm test`.
7. Append `## 15. Phase 3 Result` to `README_FIX_ALL.md`.
8. Stop. Do not start Phase 4.

After each work item, confirm the working tree is sane:

```powershell
cd E:\UNUtrip\backend\nodejs
npm test
```

If any test fails, stop and revert the most recent change with
`git restore <file>` (do NOT commit failures).

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

These are the Phase 1/2 tests (`ragContract`, `ragUpstream`, `health`,
`ai-rag-chat.route`). Phase 3 does not add new tests; it must keep all of
the above passing.

### 8.2 In-process deep route probe (optional but recommended)

If you want a stronger guarantee that no endpoint shape regressed, write
a throwaway script `_verify_phase3.mjs` at `backend/nodejs/` that uses
`supertest` to hit every protected endpoint with no JWT and confirms each
returns exactly:

```
401 { success: false, message: "Unauthorized", data: null }
```

plus header `X-Request-ID`. The full list of 29 protected endpoints is
in §4.1 of the parent `README_FIX_ALL.md`. Delete the script after
running. Phase 2 already established the baseline — see commit
`2057944`’s message.

### 8.3 Live smoke (only if you have MySQL up and `.env` configured)

If MySQL is reachable on `127.0.0.1:3306` and `.env` is set:

```powershell
npm start
```

Then in another terminal:

```powershell
# Get a token first.
$tok = (Invoke-RestMethod -Uri http://localhost:3000/api/auth/login -Method POST -ContentType "application/json" -Body '{ "email":"<your email>", "password":"<your pw>" }').token
$hdr = @{ Authorization = "Bearer $tok" }

# 1) suggest-itinerary (work item A): expect 200 with itinerary block, or 502 if RAG/AI down.
Invoke-RestMethod -Uri http://localhost:3000/api/ai/suggest-itinerary -Method POST -ContentType "application/json" -Headers $hdr -Body '{ "preferences":["beach"], "startDate":"2026-06-01", "endDate":"2026-06-03" }'

# 2) save-ai (work item D): expect 200 with success:true. The PII console.log line
#    must NOT appear in the server log.
Invoke-RestMethod -Uri http://localhost:3000/api/itineraries/save-ai -Method POST -ContentType "application/json" -Headers $hdr -Body '{ "title":"Test","description":"x","startDate":"2026-06-01","endDate":"2026-06-01","days":[] }'

# 3) create-from-option (work item B): try with empty days to get 400.
Invoke-RestMethod -Uri http://localhost:3000/api/itineraries/create-from-option -Method POST -ContentType "application/json" -Headers $hdr -Body '{ "title":"Test","startDate":"2026-06-01","endDate":"2026-06-02","days":[] }'

# 4) create-from-selection (work item C): try with empty selection to get 400.
Invoke-RestMethod -Uri http://localhost:3000/api/itineraries/create-from-selection -Method POST -ContentType "application/json" -Headers $hdr -Body '{ "title":"Test","startDate":"2026-06-01","endDate":"2026-06-02","selectedDestinations":[] }'
```

If MySQL is not up: skip the live smoke. The unit tests already exercise
app boot via Supertest, which is sufficient.

### 8.4 Failure-mode sanity test (highly recommended for work item B & C)

To prove the new `withTransaction` boundary actually rolls back, temporarily
make one of the day inserts fail (e.g. pass a non-existent `itineraryId` or
break the SQL string in a local copy). Confirm that NO `itineraries` /
`itinerary_days` / `itinerary_items` row is left in the DB. Revert the
sabotage before committing. (Skip this if you don’t have a DB handy.)

---

## 9. Pass criteria

Phase 3 is done when **ALL** of the below are true:

1. The 4 required work items (A, B, C, D) are implemented.
2. `npm test` shows `4 passed (4)` test files / `7 passed (7)` tests.
3. `git status` shows changes ONLY in the files listed in §5.1 (plus
   `README_FIX_ALL.md` if you appended the result section; plus the
   single optional new file from §5.2 if you did work item F).
4. The response body of every endpoint in §4.1 — including the success
   path and the `no_mapped_destinations` / `invalid_dates` failure paths —
   matches the pre-Phase-3 shape byte-for-byte.
5. The Vietnamese strings in the new service code remain byte-identical
   (`"Lịch trình AI tạo"`, `"Tạo bởi Hướng dẫn viên du lịch ảo."`,
   `"Lịch trình AI"`, `"Đã lưu từ gợi ý AI."`, `"Được chọn từ AI tour"`,
   `"Được chọn từ AI gợi ý"`, `"Đã tạo lịch trình bằng AI thành công!"`,
   `"Đã lưu lịch trình thành công!"`, `"Tạo lịch trình từ tour AI thành công"`,
   `"Tạo lịch trình từ AI gợi ý thành công"`).
6. The repository public API is unchanged (no edits to any
   `*.repository.js`).
7. `withTransaction` is used in exactly two new call sites (work items B
   and C) — and optionally one more for work item E. It is NOT used in
   the controller layer.
8. No new dependency was added.
9. The `console.log(JSON.stringify(req.body)...)` line in
   `saveAiItinerary` is gone.

## 9.1 Fail criteria — stop immediately if any of these happen

- A test that passed before Phase 3 now fails.
- An endpoint returns a different status code, a different response shape,
  or a different Vietnamese string than before.
- `db.pool.getConnection()` appears anywhere outside `withTransaction.js`.
- The schema or any repository SQL was modified.
- Any file listed in §6 was edited.
- A new dependency was added to `package.json`.

If any of these happen, revert the offending change with
`git restore <file>` and re-evaluate before continuing.

---

## 10. Handoff prompt for the new agent

> Copy/paste exactly this into the new Cursor Agent chat. Do not abbreviate.

```
You are continuing the UnuTrip graduation-project backend refactor.

CONTEXT:
- Repo root: E:\UNUtrip.
- The Node backend lives in backend/nodejs/.
- There is a Phase 3 plan at repo root: README_FIX_ALL_PHASE3.md.
- Phase 1 (shared plumbing) and Phase 2 (module shell migration) have
  already been completed and committed. Working tree is clean.
- An Android app consumes backend/nodejs over HTTP. backend/nodejs proxies
  AI work to backend/rag. The current system works and must not break.

TASK:
1. Read README_FIX_ALL_PHASE3.md fully. Treat it as the authoritative plan.
   You do NOT need to read README_FIX_ALL.md unless the Phase 3 plan
   references a specific section of it.
2. Implement Phase 3 exactly as described:
   - Work items A, B, C, D are REQUIRED.
   - Work items E and F are OPTIONAL — only do them if A–D land green
     with the test suite still passing.
3. Touch ONLY the files listed in section 5.1 ("Allowed files: MAY EDIT")
   and at most one new file from section 5.2 ("MAY CREATE").
4. Do NOT touch any file listed in section 6 ("Forbidden files in Phase 3"),
   especially: routes, repositories, services other than ai.service.js and
   itineraries.service.js, admin.js, db.js, auth.js, config, lib, schemas,
   middlewares, app.js, shared/http, withTransaction.js, tests, package.json,
   backend/rag, Android sources.
5. Preserve the Android API contract (section 4.1) and the RAG contract
   (section 4.2) byte-for-byte. Vietnamese strings are part of the
   contract — do not change a single character.
6. Do not modify the database schema or any repository.
7. After each work item, run `npm test` from backend/nodejs/. If any test
   regresses, revert and stop.
8. After all required work items are done, append a "Phase 3 Result"
   section to README_FIX_ALL.md (section 15). Then STOP. Do not start
   Phase 4.
9. If you encounter any ambiguity, stop and ask the user before writing
   code. Especially: if a Vietnamese string is unclear, do NOT guess —
   ask.

DELIVERABLES:
- Edits to backend/nodejs/src/services/itineraries.service.js
  (createItineraryFromAiOption + createItineraryFromAiSelection wrapped
   in withTransaction; optionally saveAiItinerary refactored too).
- Edits to backend/nodejs/src/modules/ai/ai.controller.js (suggestItinerary
  transaction moved to a new service function).
- Edits to backend/nodejs/src/modules/itineraries/itineraries.controller.js
  (drop the PII console.log line).
- ONE new service function (persistAiSuggestedItinerary) added to either
  itineraries.service.js or ai.service.js — your choice, document it in
  the result section.
- Optionally: backend/nodejs/src/shared/utils/timeSlots.js (work item F).
- A short append to README_FIX_ALL.md describing what shipped.
- Test result + summary of changes.

Start now by reading README_FIX_ALL_PHASE3.md only, then list the files
you intend to edit, then proceed.
```

---

*End of `README_FIX_ALL_PHASE3.md`. After Phase 3 ships, this document
remains in the repo as historical context; it does not need to be updated.
Phase 4 will get its own handoff doc (`README_FIX_ALL_PHASE4.md`) when the
time comes.*
