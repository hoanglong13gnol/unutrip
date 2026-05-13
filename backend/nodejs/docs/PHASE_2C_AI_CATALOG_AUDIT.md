# Phase 2C — AI catalog audit (`listDestinationsForAiSuggestion`)

Documentation of the **post–Phase 2C** audit for `ai.repository.listDestinationsForAiSuggestion()` and whether it can switch from **`destinations`** to **`app_places`**. Source code was **not** changed for this audit.

## 1. Current function

**File:** `backend/nodejs/src/repositories/ai.repository.js`  
**Function:** `listDestinationsForAiSuggestion()`

**Current SQL:**

```sql
SELECT id, name, category, rating, latitude, longitude, tags_json FROM destinations
```

There is **no** `WHERE`, **`ORDER BY`**, or **`LIMIT`** in the repository query; the full result set is returned to Node.

## 2. Caller and prompt usage

**Caller:** `backend/nodejs/src/services/ai.service.js` → `generateSuggestItineraryAiResult()`.

**Mapping:** Each row is mapped to a plain object used only for prompt construction:

| DB column   | Prompt / object field |
|------------|------------------------|
| `id`       | `id`                   |
| `name`     | `name`                 |
| `category` | `category`             |
| `rating`   | `rating`               |
| `latitude` | `latitude`             |
| `longitude`| `longitude`            |
| `tags_json`| **`tags`** (via `parseJsonArray(d.tags_json, [])`) |

**Prompt embedding:** The mapped array is sliced and stringified into the model prompt:

- `destinationsInfo.slice(0, 50)` — only the **first 50** mapped rows are included in the prompt text.

The model is instructed to return itinerary JSON using **`destinationId`** values that match those **`id`** values.

## 3. Structural `app_places` compatibility

From **`database/migrations/001_create_app_places.sql`** (schema evidence in repo), **`app_places`** defines the same **column names** needed for a drop-in `SELECT`:

- `id`, `name`, `category`, `rating`, `latitude`, `longitude`, `tags_json`

**Caveat (behavior, not names):** `database/migrations/006_populate_app_places.sql` documents that **`rating`** / aggregates may follow **review-derived** rules and **`category`** may be coerced into the controlled enum (including `'other'`). A future table swap can be **column-compatible** but still **change prompt content** vs legacy `destinations` rows.

## 4. Runtime blocker (local parity attempt)

**App config:** Root `.env` used by Node (`backend/nodejs/src/db.js`) — **`DB_NAME=unudata`**.

**Parity audit outcome (this environment):**

| Check | Result |
|--------|--------|
| `SELECT COUNT(*) FROM destinations` | **`5592`** rows |
| `SELECT COUNT(*) FROM app_places` | **Failed** — table missing |
| Error | `Table 'unudata.app_places' doesn't exist` |

**Access method note:** The `mysql` client was not available on `PATH`; checks used **`mysql2`** against the same DB settings as the app. No repository or route files were modified.

## 5. Decision

**Do not** switch `listDestinationsForAiSuggestion()` from **`destinations`** to **`app_places`** yet.

A **table-only** change to `FROM app_places` would **fail at runtime** in the current **`unudata`** environment because **`app_places` does not exist** there, which would break **`POST /ai/suggest-itinerary`** (and any other path using this catalog).

## 6. Remaining risks before a future switch

| Risk / gap | Why it matters |
|------------|----------------|
| **Database with both tables** | Parity SQL (counts, anti-joins, mismatch samples) must run on a **v2-capable** database (e.g. migrated `unudata` or a documented test DB such as `unudata_v2_test`). |
| **Row coverage** | Confirm **no** `destinations.id` without `app_places.id` (and whether **extra** `app_places` rows without `destinations` matter for this catalog). |
| **Field mismatch sample** | Compare joined rows for the seven columns; **rating** and **category** are the highest-risk divergences per migration design. |
| **Rating / category parity policy** | Decide whether AI prompts should match **legacy `destinations`** values or **v2 `app_places`** semantics (reviews-driven rating, enum category). |
| **Ordering** | Today: SQL has **no `ORDER BY`**, then **`.slice(0, 50)`** — order is **not guaranteed**. Any switch should include an **explicit `ORDER BY`** policy if stable catalogs are required. |
| **`WHERE is_active = 1`** | Not used today; adding it **excludes inactive rows** and changes which 50 rows appear — a deliberate **behavior** change, not a neutral table swap. |

## 7. Recommended future audit

Before changing **`ai.repository.js`**:

1. Point the audit (or app) at a MySQL database where **`app_places` exists** and migrations have been applied as expected.
2. Re-run parity checks, including at minimum:
   - row counts for `destinations` vs `app_places`;
   - missing / extra rows on `id`;
   - sampled column mismatches for the seven catalog fields;
   - `is_active` distribution if filtering is considered;
   - optional comparison of **`LIMIT 50`** without `ORDER BY` on both tables to illustrate **non-deterministic** catalog drift.
3. Only then decide: **table-only swap**, **`ORDER BY`**, **`is_active` filter**, and whether **`listDestinationsForAiSuggestion`** should read **`app_places`** exclusively or behind a flag.

---

*Docs-only checkpoint; does not replace migration runbooks or production validation.*
