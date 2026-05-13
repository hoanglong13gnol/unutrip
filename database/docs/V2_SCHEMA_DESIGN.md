# V2 Schema Design (Documentation Only)

**Status:** Schema design documentation. No migration SQL is defined in this document.

**Authoritative inputs for this phase:**  
`README.md`, `docs/DATA_INVENTORY.md`, `docs/CURRENT_DATABASE_AUDIT.md`, `docs/IMAGE_DATA_AUDIT.md`, `docs/V2_DATABASE_DIRECTION.md`, `docs/MIGRATION_RISK_REPORT.md`.

**Confirmed decisions (this design follows):**

- Primary migration source: `unudata-v2.sql` / current live DB (`unudata`). `backend/nodejs/database.sql` is legacy reference only.
- `app_places` is the main structured table for Android / app / API; populated from `destinations`.
- `rag_knowledge_base` is the main knowledge table for backend / RAG / AI; populated from `rag_places` and `backend/rag/data/processed/places_rag_documents.jsonl`.
- `place_images` is the source of truth for approved runtime images; `app_places.primary_image_url` is optional denormalized convenience only.
- `app_places.id` must reuse `destinations.id` during the first v2 migration.
- `place_id_map` is mandatory during migration.
- Legacy tables are not dropped until v2 passes parity checks (see `VALIDATION_CHECKLIST.md`).
- App `rating` / display aggregates must come from `reviews`, not RAG `quality_score`. `quality_score` belongs only in `rag_knowledge_base`.

---

## Design principles

1. **Two primary domains:** app contract (`app_places`) vs retrieval / grounding (`rag_knowledge_base`). User and itinerary data stay in separate product tables.
2. **Stable linkage:** `place_key` (and `place_id_map`) bridge numeric app ids, legacy `destinations.id`, `rag_place_id` / `place_id`, and assets such as image folder names where applicable.
3. **Images:** Normalized `place_images` first; `primary_image_url` optional for list performance.
4. **Legacy coexistence:** Old tables (`destinations`, `rag_places`, `destination_images`, etc.) remain until cutover validation succeeds.

---

## Table specifications

Each subsection uses this structure: purpose, source, fields (with recommended types and nullability), indexes, relationships, migration notes, open questions.

**Type notes:** Exact MySQL/MariaDB types and lengths are not fully specified in the audit docs; `recommended_type` uses SQL-family wording. Final DDL is deferred.

---

### `app_places` (proposed v2 primary app table)

**Purpose:** Structured, API-facing place rows for Android lists, detail, maps, nearby search, favorites, reviews, and itinerary items—replacing the overloaded `destinations` role for the app contract.

**Source table/file:** `destinations` in `unudata-v2.sql` / live `unudata`.

| Field | recommended_type | required | notes |
|--------|------------------|----------|-------|
| `id` | `BIGINT` or `INT`, PK (no id remap in first cut) | NOT NULL | **Must reuse** legacy `destinations.id` in first v2 migration. |
| `place_key` | `VARCHAR(...)` or `CHAR(...)`, `UNIQUE` | NOT NULL | Stable shared key; direction: align with `rag_place_id` / `place_id` where possible. |
| `name` | `VARCHAR` | NOT NULL | From `destinations.name`. |
| `description` | `TEXT` | NULL | From `destinations.description`. |
| `short_description` | `TEXT` or `VARCHAR` | NULL | From `destinations.short_description`. |
| `address` | `VARCHAR` | NULL | From `destinations.address`. |
| `city` | `VARCHAR` | NULL | From `destinations.city`. |
| `province` | `VARCHAR` | NULL | From `destinations.province`. |
| `area` | `VARCHAR` | NULL | From `destinations.area`. |
| `latitude` | `DECIMAL` | NULL | From `destinations.latitude`. |
| `longitude` | `DECIMAL` | NULL | From `destinations.longitude`. |
| `category` | `VARCHAR` | NOT NULL | Canonical app category; from `destinations.category`; must stay within controlled list per direction. |
| `open_time` | time-like (e.g. `TIME` or `VARCHAR`) | NULL | From `destinations.open_time`. |
| `close_time` | time-like | NULL | From `destinations.close_time`. |
| `entry_fee` | `VARCHAR` or numeric + currency | NULL | From `destinations.entry_fee`. |
| `budget_level` | `VARCHAR` / `INT` / enum TBD | NULL | From `destinations.budget_level`. |
| `walking_level` | same | NULL | From `destinations.walking_level`. |
| `kid_friendly` | `BOOLEAN` or `TINYINT` | NULL | From `destinations.kid_friendly`. |
| `elderly_friendly` | `BOOLEAN` or `TINYINT` | NULL | From `destinations.elderly_friendly`. |
| `recommended_use` | `VARCHAR` or `TEXT` | NULL | From `destinations.recommended_use`. |
| `tags_json` | `JSON` or `TEXT` | NULL | From `destinations.tags_json`. |
| `primary_image_url` | `VARCHAR` | NULL | Denormalized convenience only; must not replace `place_images` as SoT. |
| `rating` | `DECIMAL` | NULL | **Must** be derived from `reviews` aggregate, not RAG `quality_score`. |
| `review_count` | `INT` | NULL | Derived from `reviews`. |
| `is_active` | `BOOLEAN` / `TINYINT` | NOT NULL | From `destinations.is_active` (default TBD). |
| `created_at` | `DATETIME(3)` or `TIMESTAMP` | NULL | From `destinations` timestamps if present. |
| `updated_at` | `DATETIME(3)` or `TIMESTAMP` | NULL | Same. |

**Indexes (recommended):**

- PK on `id`.
- Unique on `place_key`.
- Composite or single-column indexes on `(province, city)`, `(latitude, longitude)` / spatial (type TBD), `category`, `is_active` as needed for list/nearby queries.

**Relationships:**

- One-to-many: `place_images`, `reviews`, `favorites`, `itinerary_items` (via app place id).
- Logical link: `rag_knowledge_base.app_place_id` → `app_places.id`; `rag_knowledge_base.place_key` ↔ `app_places.place_key`.
- `place_id_map.new_app_place_id` → `app_places.id` (same numeric value as `old_destination_id` in first cut).

**Migration notes:**

- Row count of active `app_places` should match expected active `destinations` (per risk report).
- `app_places.id` must equal source `destinations.id` for first cut; no numeric id reassignment.
- Do not copy RAG-only heavy fields into `app_places` (per direction).

**Open questions:**

- Exact storage types for `open_time` / `close_time` and `entry_fee` as used today in dump (not fully specified in audit list).
- Whether `category_main` / `category_sub` on `destinations` are retained on `app_places` or fully subsumed by single `category` (audit notes duplication with `rag_places`).
- Default for `is_active` when source row is ambiguous.

---

### `rag_knowledge_base` (proposed v2 primary RAG table)

**Purpose:** Textual and retrieval-oriented knowledge for AI / RAG (BM25, hybrid retriever, prompts)—successor role to `rag_places` plus document corpus from JSONL.

**Source table/file:** `rag_places` in `unudata-v2.sql`; `backend/rag/data/processed/places_rag_documents.jsonl`; optionally other processed JSON mentioned in data inventory (not all fields enumerated in direction).

| Field | recommended_type | required | notes |
|--------|------------------|----------|-------|
| `id` | `BIGINT`, PK, auto | NOT NULL | New surrogate id for knowledge rows. |
| `knowledge_key` | `VARCHAR`, UNIQUE | NOT NULL | Stable id for the knowledge record (generation rule TBD). |
| `place_key` | `VARCHAR` | NULL | Links to `app_places.place_key` when place-centric. |
| `app_place_id` | `BIGINT`, FK nullable | NULL | Optional FK to `app_places.id`. |
| `title` | `VARCHAR` | NULL | From `rag_places.name` or document title from JSONL (mapping TBD). |
| `knowledge_type` | `VARCHAR` or enum | NOT NULL | e.g. `place`, `itinerary`, `constraint`, … per direction; values not fully enumerated in audit. |
| `content` | `LONGTEXT` | NULL | Main body; from description / document text. |
| `summary` | `TEXT` | NULL | Align with `short_description` or JSONL summary if present. |
| `province`, `city`, `area` | `VARCHAR` | NULL | From `rag_places`. |
| `category_main`, `category_sub` | `VARCHAR` | NULL | Detailed taxonomy; RAG-facing. |
| `tags_json` | `JSON` / `TEXT` | NULL | Direction + `rag_places` metadata. |
| `interest_tags_json` | `JSON` / `TEXT` | NULL | From `rag_places` interest JSON. |
| `suitable_for_json`, `avoid_for_json` | `JSON` / `TEXT` | NULL | From `rag_places`. |
| `budget_level`, `walking_level`, `activity_level` | `VARCHAR` / `INT` | NULL | From `rag_places`. |
| `kid_friendly`, `elderly_friendly` | `BOOLEAN` | NULL | From `rag_places`. |
| `best_time_of_day_json` | `JSON` / `TEXT` | NULL | From `rag_places`. |
| `slot` | `VARCHAR` | NULL | Scheduling hint. |
| `duration_minutes` | `INT` | NULL | From `rag_places` duration concept. |
| `quality_score` | `DECIMAL` or `FLOAT` | NULL | **RAG/curation only**; not app star rating. |
| `recommended_use` | `VARCHAR` / `TEXT` | NULL | From `rag_places`. |
| `must_not_schedule_as_main` | `BOOLEAN` | NULL | From `rag_places`. |
| `requires_realtime_check` | `BOOLEAN` | NULL | From `rag_places` realtime flags. |
| `realtime_fields_json` | `JSON` / `TEXT` | NULL | From `rag_places`. |
| `is_generic` | `BOOLEAN` | NULL | From `rag_places`. |
| `source`, `source_url` | `VARCHAR` | NULL | Provenance. |
| `last_updated` | `DATETIME` | NULL | From `rag_places.last_updated`. |
| `embedding_status` or `index_status` | `VARCHAR` | NULL | Direction suggests; runtime meaning TBD. |
| `search_text` | `LONGTEXT` | NULL | From `rag_places.search_text`. |
| `raw_json` or `source_payload_json` | `LONGTEXT` / `JSON` | NULL | From `rag_places.raw_json`; heavy; audit notes size. |
| `is_active` | `BOOLEAN` | NOT NULL | Default TBD. |
| `created_at`, `updated_at` | `DATETIME` | NULL | If not in source, set at migration. |

**Indexes (recommended):**

- PK on `id`.
- Unique on `knowledge_key`.
- Index on `place_key`, `app_place_id`, `(province, city)`, `knowledge_type`, `is_active`.
- Fulltext on `search_text` / `content` if DB supports and product chooses (not confirmed).

**Relationships:**

- Optional FK `app_place_id` → `app_places.id`.
- Logical link `place_key` → `app_places.place_key`.
- Populated from `rag_places.destination_id` / `place_id` via `place_id_map` when resolving `app_place_id`.

**Migration notes:**

- Merge strategy for one `rag_places` row vs many JSONL documents per place is not specified in audit—see Open Questions.
- Do not push `quality_score` into app rating fields.

**Open questions:**

- Exact columns in `places_rag_documents.jsonl` (not listed line-by-line in authorized docs).
- How `knowledge_key` is generated for JSONL-only documents vs `rag_places` rows.
- Whether itinerary/constraint docs from JSONL get separate `knowledge_type` values and mandatory fields.
- Whether `embedding_status` / `index_status` are persisted in DB or only in RAG runtime files.

---

### `place_images` (proposed v2 approved image table)

**Purpose:** Source of truth for approved runtime images attached to app places.

**Source table/file:** `destination_images` in `unudata-v2.sql`; backfill from `destinations.images_json` where rows missing; local files under `backend/nodejs/public/images/destinations/` referenced by URLs.

| Field | recommended_type | required | notes |
|--------|------------------|----------|-------|
| `id` | `BIGINT`, PK | NOT NULL | New id or preserve `destination_images.id` (decision TBD). |
| `app_place_id` | `BIGINT`, FK | NOT NULL | Maps from `destination_images.destination_id`. |
| `place_key` | `VARCHAR` | NULL | Optional; from `destination_images.rag_place_id` or `app_places.place_key`. |
| `image_url` | `VARCHAR` | NOT NULL | `/images/...` or external URL. |
| `storage_type` | `VARCHAR` / enum | NULL | Direction suggests `local`, `external`, `upload`; exact enum TBD. |
| `source` | `VARCHAR` | NULL | Provenance. |
| `source_page_url` | `VARCHAR` | NULL | Direction recommends; `destination_images` audit list does not confirm column—may need backfill from `images_json` objects. |
| `credit` | `VARCHAR` | NULL | From `destination_images.credit`. |
| `license_note` | `VARCHAR` / `TEXT` | NULL | From `destination_images.license_note`. |
| `sort_order` | `INT` | NULL | Direction recommends; source may use only `is_primary`. |
| `is_primary` | `BOOLEAN` | NOT NULL | From `destination_images.is_primary`. |
| `status` | `VARCHAR` | NOT NULL | Active vs inactive; align with current `destination_images.status` semantics. |
| `created_at`, `updated_at` | `DATETIME` | NULL | From source or migration. |

**Indexes (recommended):**

- PK on `id`.
- Index on `app_place_id`, partial/filtered unique on `(app_place_id)` where `is_primary = true` (one primary per place—product rule, confirm).
- Index on `place_key` if used.
- Index on `status` for “active only” queries.

**Relationships:**

- FK `app_place_id` → `app_places.id`.
- Optional logical link to `rag_knowledge_base` via `place_key` only (not necessarily FK).

**Migration notes:**

- Prefer active `destination_images` over `images_json` (image audit).
- Verify local paths resolve to existing files.

**Open questions:**

- Exact allowed values for `status` in current DB.
- Whether to preserve `destination_images.id` for traceability.
- Max images per place and uniqueness rules (URL dedup).

---

### `place_image_candidates` (proposed; optional staging)

**Purpose:** Staging / review for image collection (operations, not app runtime contract).

**Source table/file:** `destination_image_candidates` in `unudata-v2.sql` (fields: candidate URL, source page, provider, confidence, review notes, candidate status, batch code per audit).

| Field | recommended_type | required | notes |
|--------|------------------|----------|-------|
| `id` | `BIGINT`, PK | NOT NULL | |
| `app_place_id` or legacy `destination_id` | `BIGINT` | NULL | Map after cutover to `app_place_id`; interim mapping via `place_id_map`. |
| `candidate_url` | `VARCHAR` | NOT NULL | Per audit. |
| `source_page_url` | `VARCHAR` | NULL | Per audit. |
| `provider` | `VARCHAR` | NULL | |
| `confidence` | `DECIMAL` | NULL | |
| `review_notes` | `TEXT` | NULL | |
| `candidate_status` | `VARCHAR` | NOT NULL | |
| `batch_code` | `VARCHAR` | NULL | |
| Timestamps | `DATETIME` | NULL | If present in source. |

**Indexes:** PK; indexes on `app_place_id`, `candidate_status`, `batch_code`.

**Relationships:** Optional FK to `app_places.id` once ids resolved.

**Migration notes:** Direction: keep outside app runtime if curation continues; can remain as staging with renamed table.

**Open questions:**

- Whether v2 first cut renames table only vs full column normalization.
- Promotion workflow from candidate → `place_images` (procedural, not in audit DDL).

---

### `place_id_map` (mandatory)

**Purpose:** Preserve linkage across old `destinations.id`, `destinations.rag_place_id`, `rag_places.place_id`, `rag_places.destination_id`, new `app_places.id`, and `place_key`; mitigate breakage for favorites, reviews, itineraries, AI raw ids (per risk report).

**Source table/file:** Derived from `destinations`, `rag_places`, and optionally image folder names (audit); not a single source table.

| Field | recommended_type | required | notes |
|--------|------------------|----------|-------|
| `id` | `BIGINT`, PK | NOT NULL | Surrogate. |
| `old_destination_id` | `BIGINT` | NULL | Original `destinations.id`. |
| `rag_place_id_legacy` | `VARCHAR` | NULL | From `destinations.rag_place_id` if present. |
| `rag_place_id` | `VARCHAR` | NULL | `rag_places.place_id` string id. |
| `old_rag_destination_id` | `BIGINT` | NULL | `rag_places.destination_id`. |
| `new_app_place_id` | `BIGINT`, FK | NOT NULL | After `app_places` exists. |
| `place_key` | `VARCHAR` | NOT NULL | Canonical key used in v2. |
| `image_folder_key` | `VARCHAR` | NULL | Optional: slug folder name vs `rag_place_id` style (audit: inconsistent naming). |
| `notes` | `VARCHAR` | NULL | Migration exceptions. |
| `created_at` | `DATETIME` | NULL | |

**Indexes:**

- Unique on `new_app_place_id` if 1:1 map per app place (confirm).
- Unique on (`old_destination_id`) where not null.
- Unique on (`rag_place_id`) where not null, or non-unique if duplicates exist (validate).
- Index on `place_key`.

**Relationships:**

- `new_app_place_id` → `app_places.id`.

**Migration notes:**

- Validate every `rag_places.destination_id` resolves to an app place (risk report).

**Open questions:**

- How to represent one destination linked to multiple `rag_places` rows or vice versa (cardinality not fully specified).
- Handling slug-folder-only places without DB row.

---

### `users` (retained)

**Purpose:** Authentication profile, avatar, preferences.

**Source table/file:** `users` in `unudata-v2.sql`.

**Fields / types:** Per current dump (not expanded in authorized docs). Treat as carry-forward.

**Indexes / relationships:** PK on user id; referenced by `favorites`, `reviews`, `itineraries`.

**Migration notes:** Risk: sensitive/test user data—classification and whether v2 starts clean or migrates users is an organizational decision (risk report).

**Open questions:**

- Whether any columns are renamed in v2 naming cleanup (not specified).

---

### `favorites` (retained, FK target changes conceptually)

**Purpose:** User-saved places.

**Source table/file:** `favorites` in `unudata-v2.sql`; currently references destination id per audit.

| Field | recommended_type | required | notes |
|--------|------------------|----------|-------|
| User id | FK | NOT NULL | |
| Place id | FK | NOT NULL | Must become `app_places.id` after migration; old column referenced `destinations.id`. |

**Indexes:** Composite unique (user, place) typical; confirm in dump.

**Relationships:** `user_id` → `users.id`; `app_place_id` → `app_places.id`.

**Migration notes:** Remap using `place_id_map.old_destination_id` → `new_app_place_id`.

**Open questions:**

- Exact current column names in `favorites` (not listed in audit).

---

### `reviews` (retained)

**Purpose:** User reviews; source of truth for app rating aggregation.

**Source table/file:** `reviews` in `unudata-v2.sql`.

**Fields:** Review text, rating, images (`images_json` per typical app patterns); audit mentions review images and uploads.

**Indexes:** On `destination_id` / future `app_place_id`, `user_id`.

**Relationships:** To `users`, to app place via FK.

**Migration notes:** Remap destination id to `app_places.id`; recompute `app_places.rating` and `review_count` from aggregates.

**Open questions:**

- Whether to split review images into `review_images` (direction: optional); not required in first doc phase.

---

### `itineraries` / `itinerary_days` / `itinerary_items` (retained)

**Purpose:** Manual and AI-created trip structures.

**Source table/file:** `itineraries`, `itinerary_days`, `itinerary_items` in `unudata-v2.sql`.

**Migration notes:** `itinerary_items` destination references must map to `app_places.id`. Node resolves AI `rawPlaceId` via `rag_places` today—post-migration must still resolve via `place_id_map` / `rag_knowledge_base` linkage (behavior doc only).

**Open questions:**

- Exact FK column names on itinerary tables in dump.

---

### `priority_place_tiers` (retained legacy / operational)

**Purpose:** Ranking / priority seed for image coverage and scoring scripts.

**Source table/file:** `priority_place_tiers` in `unudata-v2.sql`.

**Migration notes:** Direction: may fold into curated metadata or rename later; not dropped until parity.

**Open questions:**

- Final v2 name (`place_priority_tiers` vs keep name); whether data merges into `app_places` / `rag_knowledge_base` later.

---

### Legacy tables not dropped until parity (document only)

| Table | Purpose (short) | Notes |
|--------|-----------------|-------|
| `destinations` | Current app-facing place table | Becomes read-only legacy after `app_places` populated; compare counts during validation. |
| `rag_places` | Current RAG place table | Legacy after `rag_knowledge_base` populated. |
| `destination_images` | Current normalized images | Legacy after `place_images` populated. |
| `destination_image_candidates` | Staging images | Legacy parallel to `place_image_candidates` if renamed. |

---

## Optional / future tables (direction only; cut scope TBD)

These appear in `docs/V2_DATABASE_DIRECTION.md` but are not mandatory for the narrative above:

- `review_images` — normalize review attachments.
- `place_aliases` — search / dedupe.
- `place_taxonomy` — category labels, icons, ordering.
- `data_import_batches` — import audit trail.

**Open questions:** Which optional tables ship in the first v2 schema vs later iterations.

---

## Cross-reference

- Field-level dictionary: `TABLE_FIELD_DICTIONARY.md`.
- Old → new mapping rules: `OLD_TO_NEW_MAPPING.md`.
- Images: `IMAGE_MIGRATION_PLAN.md`.
- RAG ingest: `RAG_SYNC_FLOW.md`.
- Validation: `VALIDATION_CHECKLIST.md`.
