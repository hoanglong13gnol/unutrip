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

## Locked decisions (confirmed)

- **App place id reuse (mandatory)**: `app_places.id` must reuse `destinations.id` in the first v2 migration.
  - Legacy evidence: `destinations.id` is `int(11)` primary key with AUTO_INCREMENT in the dump.
- **No new `app_places` ids generated in first cut**: numeric remap is explicitly disallowed in the current plan.
- **`place_id_map` remains mandatory** even though numeric ids are reused:
  - Required for `rag_place_id`, RAG `place_id`, AI `rawPlaceId`, image folder keys, and relationship tracing across legacy/v2.

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

- **Not reliable from legacy dump alone (must be locked as rules / Open Questions)**:
  - `place_key`: legacy has `destinations.rag_place_id` nullable + `rag_places.place_id` non-null unique; but **generation/resolution when `destinations.rag_place_id` is NULL** is not defined by schema.
  - `primary_image_url`: legacy has `destinations.images_json` plus normalized `destination_images` rows, but **exact precedence and derivation rules** must be locked (policy exists in docs; still requires precise rule).

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

- **Not reliable from legacy dump alone**:
  - `source_page_url`: **no column** exists in `destination_images`. May exist inside `destinations.images_json` objects for some rows, but presence/shape is not guaranteed by schema.
  - `sort_order`: **no column** exists in `destination_images`. Some ordering appears in `destinations.images_json` objects (`order`), but not schema-guaranteed.
  - `storage_type`: not present in legacy schema; would require inference from URL/path rules.

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

- **Not reliable from legacy dump alone (requires external definition / Open Questions)**:
  - `knowledge_key`: not present in `rag_places`; would require a generation rule or JSONL field.
  - `knowledge_type` allowed values: not present in `rag_places`; requires product/schema decision.
  - JSONL field list + merge/cardinality rules: cannot be inferred from `unudata-v2.sql`.
  - `embedding_status` / `index_status`: not present in `rag_places` schema.

---

## Decisions to lock next (before migration SQL)

These must be resolved explicitly; otherwise migration SQL cannot be “database-first and deterministic”.

- **`place_key` definition and precedence**
  - Candidate sources:
    - `destinations.rag_place_id` (nullable, unique when not null)
    - `rag_places.place_id` (non-null, unique)
    - `destination_images.rag_place_id` (nullable)
  - Required: deterministic rule for cases where:
    - `destinations.rag_place_id` is NULL
    - A destination has images with `rag_place_id` but the destination does not
    - Any mismatch between `rag_places.destination_id` and destination row’s `rag_place_id`

- **Primary image derivation**
  - If `destination_images` has 1+ rows for a destination:
    - rule for choosing primary (`is_primary`? first by id? other?) must be locked.
  - When `destination_images` has zero rows:
    - whether/how to parse `destinations.images_json` (string list vs object list) must be locked.

- **`destination_images.status` semantics**
  - Only `active` is observed in the dump, but migration must define:
    - whether other statuses are possible in production (and how they map to v2).

- **`destinations.category` controlled list**
  - The dump shows exactly 9 values used. Lock this as the initial controlled list (unless direction doc says otherwise) and decide how to handle:
    - legacy default `other` (exists as default but not observed in inserted data)

---

## Open Questions (do not guess)

1. **`place_key` rule when `destinations.rag_place_id` is NULL**: generate new key vs derive from other legacy fields vs allow null?
2. **Image metadata gap**:
   - Should v2 persist `source_page_url` and `sort_order`?
   - If yes, is legacy `destinations.images_json` considered authoritative enough, and what are accepted shapes (string vs object)?
3. **RAG JSONL integration**:
   - Exact schema/fields in `places_rag_documents.jsonl` (not represented in `unudata-v2.sql`).
   - Cardinality: one row per place vs many knowledge rows per place.
   - `knowledge_key` generation rule.
   - Allowed values list for `knowledge_type`.
4. **`rag_places.last_updated` type**:
   - Legacy type is `varchar(50)`; if v2 uses `DATETIME`, define parse rules and failure handling.
5. **Whether any legacy-only fields remain required in v2 validation**:
   - `destinations.images_json`, `image_source`, `image_credit` exist in schema; decide if they remain as legacy-only validation or are promoted into v2 tables.

