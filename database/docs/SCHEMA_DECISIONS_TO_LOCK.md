# Schema Decisions to Lock (before writing migration SQL)

**Phase:** UNUtrip v2 database-first refactor — lock decisions after exact legacy schema audit.  
**Hard rule:** This document does **not** create migration SQL; it only locks decisions and lists open questions.

## Inputs (source of truth for this phase)

- `database/docs/V2_SCHEMA_DESIGN.md`
- `database/docs/OLD_TO_NEW_MAPPING.md`
- `database/docs/TABLE_FIELD_DICTIONARY.md`
- `database/docs/VALIDATION_CHECKLIST.md`
- `unudata-v2.sql`
- Exact audit output: `database/docs/EXACT_LEGACY_SCHEMA_AUDIT.md`

---

## Locked migration decisions (must follow in first SQL migration)

- **1) `app_places.id` rule**
  - `app_places.id` must reuse `destinations.id`.
  - No new `app_places` ids are generated in the first v2 migration.

- **2) `place_key` rule**
  - If `destinations.rag_place_id` is not null, use `destinations.rag_place_id`.
  - Else if a `rag_places` row exists where `rag_places.destination_id = destinations.id`, use `rag_places.place_id`.
  - Else generate `MANUAL_{destinations.id}`.
  - Any generated `MANUAL_*` key must be recorded in `place_id_map.notes` for later manual review.

- **3) Category rule (`app_places.category`)**
  - Initial controlled list:
    - `beach`, `checkin`, `city`, `culture`, `food`, `heritage`, `mountain`, `nature`, `religious`
  - If legacy value `other` appears later, keep it but **flag it for review**.
  - Do not invent new categories during migration.

- **4) `destination_images.status` rule**
  - Only `destination_images.status = active` is migrated into runtime `place_images`.
  - Unknown or future status values must not be promoted automatically.
  - Unknown statuses must be reported for review.

- **5) Primary image rule**
  - Prefer **active** `destination_images` rows.
  - If one or more active rows have `is_primary = 1`, choose the row with the smallest `destination_images.id` as primary.
  - If no active row has `is_primary = 1`, choose the active row with the smallest `destination_images.id` as primary.
  - If there are no active `destination_images` rows, backfill from `destinations.images_json`.
  - When backfilling from `images_json`, choose the first parsed URL as primary.
  - If `images_json` cannot be parsed, leave `primary_image_url` null and report the destination id for review.

- **6) `place_images` optional fields**
  - `source_page_url`, `sort_order`, and `storage_type` are nullable.
  - They are not required for first migration success.
  - `source_page_url` and `sort_order` may be backfilled later from `images_json` or image pipeline data.

- **7) RAG first-cut rule**
  - `rag_places` is the primary source for the first `rag_knowledge_base` migration.
  - `places_rag_documents.jsonl` is not required for the first SQL migration.
  - JSONL ingestion is deferred to a later supplement phase after its schema is inspected.
  - `knowledge_key` for rows migrated from `rag_places` should be derived deterministically from `rag_places.place_id`.
  - `knowledge_type` for rows migrated from `rag_places` should be `place`.

- **8) `rag_places.last_updated` rule**
  - Keep `last_updated` as VARCHAR-compatible text in the first migration.
  - Do not convert to DATETIME in the first migration.
  - Datetime parsing can be handled in a later cleanup phase.

- **Always: `place_id_map` remains mandatory**
  - Even though numeric ids are reused, `place_id_map` is mandatory for `rag_place_id` / `place_id`, AI `rawPlaceId`, image folder keys, and legacy relationship tracing.

---

## Legacy constraints that v2 must respect (from dump)

These are not “choices” but they impact what migration must preserve.

- **FK web anchored on `destinations.id`**:
  - `favorites.destination_id` → `destinations.id` (cascade)
  - `reviews.destination_id` → `destinations.id` (cascade)
  - `itinerary_items.destination_id` → `destinations.id` (cascade)
  - `destination_images.destination_id` → `destinations.id` (cascade)
  - `rag_places.destination_id` → `destinations.id` (set null)
- **Uniqueness constraints**:
  - `destinations.rag_place_id` is `UNIQUE` (but nullable).
  - `rag_places.place_id` is `UNIQUE` and `NOT NULL`.
- **Observed enum-like value sets** (from inserted data):
  - `destinations.category` values present: `beach`, `checkin`, `city`, `culture`, `food`, `heritage`, `mountain`, `nature`, `religious`.
  - `destination_images.status` values present: `active` only.

---

## “Reliable legacy source” matrix (v2-doc fields vs legacy evidence)

Rule for this matrix:

- **Reliable** = present as a dedicated legacy column with clear meaning in `unudata-v2.sql`, or computable without guesswork from legacy relational data.
- **Not reliable** = not present in legacy schema, only implied by narrative, or requires external files/process not included in the schema dump. These must be tracked as **Open Questions** (no guessing).

### `app_places` (proposed) vs legacy

- **Reliable from `destinations`**:
  - `id` ← `destinations.id` (direct reuse)
  - `name`, `description`, `short_description`, `address`, `city`, `province`, `area`
  - `latitude`, `longitude`
  - `category` ← `destinations.category` (values present listed above)
  - `open_time`, `close_time` (legacy types: `varchar(20)`)
  - `entry_fee` (legacy type: `double`)
  - `budget_level`, `walking_level` (legacy: `varchar(50)`)
  - `kid_friendly`, `elderly_friendly` (legacy: `tinyint(1)` with defaults)
  - `recommended_use` (legacy: `varchar(50)`)
  - `tags_json` (legacy: `text` default `'[]'`)
  - `is_active` (legacy: `tinyint(1)` default `1`)
  - `created_at`, `updated_at` (legacy: `timestamp` with defaults)

- **Computed/re-derived (reliable source exists, but is not a direct copy)**:
  - `rating` / `review_count`:
    - Legacy columns exist on `destinations` (`rating double`, `review_count int`), but v2 policy says app rating must be derived from `reviews`.
    - Reliable legacy source for computation: `reviews(destination_id, rating, ...)` with FK to `destinations.id`.

- **Now locked as migration rules (see “Locked migration decisions”)**:
  - `place_key` rule (including `MANUAL_*` fallback + `place_id_map.notes`)
  - `primary_image_url` derivation/selection rule (active `destination_images` first; `images_json` backfill)

### `place_images` (proposed) vs legacy

Legacy sources: `destination_images` (normalized) and `destinations.images_json` (denormalized, mixed formats).

- **Reliable from `destination_images`**:
  - `app_place_id` ← `destination_images.destination_id` (int)
  - `place_key` candidate ← `destination_images.rag_place_id` (varchar(50), nullable)
  - `image_url` ← `destination_images.image_url` (text)
  - `source` ← `destination_images.source` (varchar(100), nullable)
  - `credit` ← `destination_images.credit` (text, nullable)
  - `license_note` ← `destination_images.license_note` (text, nullable)
  - `is_primary` ← `destination_images.is_primary` (tinyint(1) default 0)
  - `status` ← `destination_images.status` (varchar(50) default `'active'`; observed value `active` only)
  - `created_at`, `updated_at` (timestamps)

- **Not reliable from legacy dump alone, but explicitly allowed to be NULL in first migration** (locked decision):
  - `source_page_url`
  - `sort_order`
  - `storage_type`

### `rag_knowledge_base` (proposed) vs legacy

Legacy source table: `rag_places`. Additional proposed source: `backend/rag/data/processed/places_rag_documents.jsonl` (external file, not in SQL dump).

- **Reliable from `rag_places`** (schema-backed columns exist):
  - Place linkage: `place_id` (string), `destination_id` (nullable int)
  - Location/taxonomy: `province`, `city`, `area`, `category_main`, `category_sub`, and `_norm` variants
  - Text: `description`, `short_description`, `search_text`, `raw_json`
  - Operational flags: `is_generic`, `must_not_schedule_as_main`, `requires_realtime_check`, `realtime_fields_json`, `is_active`
  - Time/cost fields: `open_time`, `close_time`, `duration_minutes`, `entry_fee_min`, `entry_fee_max`, `is_free`, etc.
  - Scoring: `quality_score`
  - Source: `source`, `source_url`, `last_updated` (legacy type is `varchar(50)` for `last_updated`, not DATETIME)

- **Locked for first migration**:
  - `knowledge_key` is derived deterministically from `rag_places.place_id` for rows migrated from `rag_places`.
  - `knowledge_type = place` for rows migrated from `rag_places`.
  - JSONL (`places_rag_documents.jsonl`) ingestion is deferred (not required for first SQL migration).

- **Remaining not reliable from legacy dump alone (deferred / optional)**:
  - JSONL field list + merge/cardinality rules
  - `embedding_status` / `index_status`

---

## Remaining Open Questions (not required for first SQL migration)

1. **JSONL schema for `places_rag_documents.jsonl`**: field names, types, and linkage keys (deferred supplement phase).
2. **JSONL cardinality rules**: merge into one knowledge row per place vs keep multiple retrievable documents per place (deferred).
3. **`embedding_status` / `index_status`**: whether these are stored in MySQL vs inferred/maintained in filesystem/runtime (deferred).
4. **Image metadata backfill policy**:
   - Exact parsing/normalization rules across mixed `destinations.images_json` shapes (string list vs object list) beyond “first URL as primary”.
   - Backfill sources priority between `images_json` objects vs image pipeline data (deferred).
5. **Reporting format/target for “must be reported” items** (unknown statuses, `MANUAL_*` keys, primary conflicts, images_json parse failures): where these reports live (table, file, or operational log) is not locked in docs yet.

