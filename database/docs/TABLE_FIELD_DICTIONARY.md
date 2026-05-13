# V2 Table / Field Dictionary

**Scope:** Documentation only. Types are **recommended**; final DDL is not defined here. Sources: project docs as listed in `V2_SCHEMA_DESIGN.md`.

**Legend**

- **required:** NOT NULL vs NULL when migrated.
- **source:** primary origin for initial population.

---

## `app_places`

| field | meaning | source | recommended_type | required | notes |
|--------|---------|--------|------------------|----------|-------|
| `id` | App place primary key | `destinations.id` | `BIGINT` or `INT` PK | NOT NULL | First v2 cut: must reuse `destinations.id` exactly. |
| `place_key` | Stable cross-system key | `destinations.rag_place_id`, `rag_places.place_id`, or new rule | `VARCHAR` UNIQUE | NOT NULL | Must stay stable for images/RAG. |
| `name` | Display name | `destinations.name` | `VARCHAR` | NOT NULL | |
| `description` | Long description | `destinations.description` | `TEXT` | NULL | |
| `short_description` | Short blurb | `destinations.short_description` | `TEXT` | NULL | |
| `address` | Street / location line | `destinations.address` | `VARCHAR` | NULL | |
| `city` | City | `destinations.city` | `VARCHAR` | NULL | |
| `province` | Province | `destinations.province` | `VARCHAR` | NULL | |
| `area` | Area / region label | `destinations.area` | `VARCHAR` | NULL | |
| `latitude` | Lat | `destinations.latitude` | `DECIMAL(9,6)` or wider | NULL | Precision TBD from dump. |
| `longitude` | Lng | `destinations.longitude` | `DECIMAL(9,6)` or wider | NULL | |
| `category` | App category code | `destinations.category` | `VARCHAR` | NOT NULL | Controlled list per direction doc. |
| `open_time` | Opening time | `destinations.open_time` | `TIME` or `VARCHAR` | NULL | Type not fixed in audit. |
| `close_time` | Closing time | `destinations.close_time` | `TIME` or `VARCHAR` | NULL | |
| `entry_fee` | Fee text or value | `destinations.entry_fee` | `VARCHAR` or numeric pair | NULL | |
| `budget_level` | Budget hint | `destinations.budget_level` | `INT` / `VARCHAR` | NULL | |
| `walking_level` | Walking difficulty | `destinations.walking_level` | `INT` / `VARCHAR` | NULL | |
| `kid_friendly` | Kid suitability | `destinations.kid_friendly` | `BOOLEAN` | NULL | |
| `elderly_friendly` | Elderly suitability | `destinations.elderly_friendly` | `BOOLEAN` | NULL | |
| `recommended_use` | Recommended usage text | `destinations.recommended_use` | `VARCHAR` | NULL | |
| `tags_json` | Tags payload | `destinations.tags_json` | `JSON` | NULL | |
| `primary_image_url` | Cached primary image URL | derive from `place_images` or legacy | `VARCHAR` | NULL | Denormalized only; not SoT. |
| `rating` | Aggregate star rating | **computed from `reviews` only** | `DECIMAL(3,2)` | NULL | Not from RAG. |
| `review_count` | Count of reviews | **computed from `reviews`** | `INT` | NULL | |
| `is_active` | Published flag | `destinations.is_active` | `BOOLEAN` | NOT NULL | |
| `created_at` | Created | `destinations` if present | `DATETIME(3)` | NULL | |
| `updated_at` | Updated | `destinations` if present | `DATETIME(3)` | NULL | |

**Open questions:** Whether `destinations.category_main` / `category_sub` are copied into `app_places` or dropped from app surface; exact datetime column names in dump.

---

## `rag_knowledge_base`

| field | meaning | source | recommended_type | required | notes |
|--------|---------|--------|------------------|----------|-------|
| `id` | Knowledge row id | new | `BIGINT` PK AI | NOT NULL | |
| `knowledge_key` | Stable document id | new or from JSONL id field | `VARCHAR` UNIQUE | NOT NULL | Generation rule TBD. |
| `place_key` | Link to app key | `rag_places.place_id`, JSONL | `VARCHAR` | NULL | Nullable for non-place docs. |
| `app_place_id` | FK to app | derived via map | `BIGINT` FK | NULL | |
| `title` | Title / name | `rag_places.name`, JSONL | `VARCHAR` | NULL | |
| `knowledge_type` | Doc kind | direction enum + JSONL type | `VARCHAR` | NOT NULL | Allowed values TBD. |
| `content` | Main text | `rag_places.description`, JSONL body | `LONGTEXT` | NULL | |
| `summary` | Short summary | `short_description`, JSONL | `TEXT` | NULL | |
| `province` | Province | `rag_places.province` | `VARCHAR` | NULL | |
| `city` | City | `rag_places.city` | `VARCHAR` | NULL | |
| `area` | Area | `rag_places.area` | `VARCHAR` | NULL | |
| `category_main` | RAG taxonomy main | `rag_places.category_main` | `VARCHAR` | NULL | |
| `category_sub` | RAG taxonomy sub | `rag_places.category_sub` | `VARCHAR` | NULL | |
| `tags_json` | Tags | `rag_places` / JSONL | `JSON` | NULL | |
| `interest_tags_json` | Interests | `rag_places` | `JSON` | NULL | |
| `suitable_for_json` | Suitability | `rag_places` | `JSON` | NULL | |
| `avoid_for_json` | Avoid list | `rag_places` | `JSON` | NULL | |
| `budget_level` | Normalized budget | `rag_places` | `VARCHAR` / `INT` | NULL | |
| `walking_level` | Walking | `rag_places` | `VARCHAR` / `INT` | NULL | |
| `activity_level` | Activity | `rag_places` | `VARCHAR` / `INT` | NULL | |
| `kid_friendly` | Flag | `rag_places` | `BOOLEAN` | NULL | |
| `elderly_friendly` | Flag | `rag_places` | `BOOLEAN` | NULL | |
| `best_time_of_day_json` | Best time | `rag_places` | `JSON` | NULL | |
| `slot` | Time slot hint | `rag_places` | `VARCHAR` | NULL | |
| `duration_minutes` | Visit duration | `rag_places` | `INT` | NULL | |
| `quality_score` | RAG / curation quality | `rag_places.quality_score` | `DECIMAL` | NULL | **Never** app star rating. |
| `recommended_use` | Text hint | `rag_places.recommended_use` | `TEXT` | NULL | |
| `must_not_schedule_as_main` | Scheduling guard | `rag_places` | `BOOLEAN` | NULL | |
| `requires_realtime_check` | Needs live check | `rag_places` | `BOOLEAN` | NULL | |
| `realtime_fields_json` | Fields needing check | `rag_places` | `JSON` | NULL | |
| `is_generic` | Generic place flag | `rag_places` | `BOOLEAN` | NULL | |
| `source` | Provenance label | `rag_places.source` | `VARCHAR` | NULL | |
| `source_url` | Source URL | `rag_places.source_url` | `VARCHAR` | NULL | |
| `last_updated` | Source refresh time | `rag_places.last_updated` | `DATETIME` | NULL | |
| `embedding_status` | Vector/index state | operational | `VARCHAR` | NULL | May be app-level only. |
| `index_status` | Index state alt | operational | `VARCHAR` | NULL | |
| `search_text` | Retrieval text | `rag_places.search_text` | `LONGTEXT` | NULL | |
| `raw_json` | Raw payload | `rag_places.raw_json` | `LONGTEXT` | NULL | Large; audit warns. |
| `is_active` | Active flag | new default | `BOOLEAN` | NOT NULL | |
| `created_at` | Created | migration | `DATETIME` | NULL | |
| `updated_at` | Updated | migration | `DATETIME` | NULL | |

**Open questions:** JSONL field list; mapping when one place has many documents; aliases / group fields on `rag_places` not enumerated in audit table (may exist in dump).

---

## `place_images`

| field | meaning | source | recommended_type | required | notes |
|--------|---------|--------|------------------|----------|-------|
| `id` | Row id | `destination_images.id` or new | `BIGINT` PK | NOT NULL | |
| `app_place_id` | Owning place | map from `destination_images.destination_id` | `BIGINT` FK | NOT NULL | |
| `place_key` | Optional key | `destination_images.rag_place_id` | `VARCHAR` | NULL | |
| `image_url` | Public URL | `destination_images.image_url` | `VARCHAR` | NOT NULL | |
| `storage_type` | local / external / upload | infer from URL + rules | `VARCHAR` | NULL | |
| `source` | Attribution source | `destination_images.source` | `VARCHAR` | NULL | |
| `source_page_url` | Page URL | JSONL/object backfill | `VARCHAR` | NULL | Not in short audit column list. |
| `credit` | Credit | `destination_images.credit` | `VARCHAR` | NULL | |
| `license_note` | License | `destination_images.license_note` | `TEXT` | NULL | |
| `sort_order` | Order | new or `images_json.order` | `INT` | NULL | |
| `is_primary` | Primary flag | `destination_images.is_primary` | `BOOLEAN` | NOT NULL | |
| `status` | Active/staging | `destination_images.status` | `VARCHAR` | NOT NULL | |
| `created_at` | Created | `destination_images` | `DATETIME` | NULL | |
| `updated_at` | Updated | `destination_images` | `DATETIME` | NULL | |

**Open questions:** `status` enum values; single-primary constraint; dedup rules.

---

## `place_image_candidates`

| field | meaning | source | recommended_type | required | notes |
|--------|---------|--------|------------------|----------|-------|
| `id` | PK | `destination_image_candidates` | `BIGINT` | NOT NULL | |
| Place reference | Link to place | source table | `BIGINT` | NULL | Map to `app_place_id`. |
| `candidate_url` | URL | source | `VARCHAR` | NOT NULL | Audit summary. |
| `source_page_url` | Page | source | `VARCHAR` | NULL | |
| `provider` | Provider | source | `VARCHAR` | NULL | |
| `confidence` | Score | source | `DECIMAL` | NULL | |
| `review_notes` | Human notes | source | `TEXT` | NULL | |
| `candidate_status` | Workflow state | source | `VARCHAR` | NOT NULL | |
| `batch_code` | Batch | source | `VARCHAR` | NULL | |

**Open questions:** Full column names list from dump; rename vs 1:1 copy.

---

## `place_id_map`

| field | meaning | source | recommended_type | required | notes |
|--------|---------|--------|------------------|----------|-------|
| `id` | PK | synthetic | `BIGINT` | NOT NULL | |
| `old_destination_id` | Legacy app id | `destinations.id` | `BIGINT` | NULL | |
| `rag_place_id_legacy` | From destination | `destinations.rag_place_id` | `VARCHAR` | NULL | |
| `rag_place_id` | RAG id | `rag_places.place_id` | `VARCHAR` | NULL | |
| `old_rag_destination_id` | rag→dest link | `rag_places.destination_id` | `BIGINT` | NULL | |
| `new_app_place_id` | v2 id | `app_places.id` | `BIGINT` FK | NOT NULL | First cut equals `old_destination_id`; map retained for cross-key linking. |
| `place_key` | Canonical key | derived | `VARCHAR` | NOT NULL | |
| `image_folder_key` | Folder name hint | filesystem / heuristic | `VARCHAR` | NULL | |
| `notes` | Manual | ops | `VARCHAR` | NULL | |
| `created_at` | Audit | migration | `DATETIME` | NULL | |

**Open questions:** 1:1 vs 1:N rows for RAG/image key aliases; handling collisions on non-numeric keys.

---

## `users` (carry-forward)

| field | meaning | source | recommended_type | required | notes |
|--------|---------|--------|------------------|----------|-------|
| (PK) | User id | `users` | integer PK | NOT NULL | Exact name TBD from dump. |
| Profile / auth fields | As today | `users` | per dump | varies | Not enumerated in audit detail. |
| Avatar | Path or URL | `users` | `VARCHAR` | NULL | Uploads under `uploads/avatars/`. |

**Open questions:** Full column list from `unudata-v2.sql` not in authorized docs.

---

## `favorites` (carry-forward, remap FK)

| field | meaning | source | recommended_type | required | notes |
|--------|---------|--------|------------------|----------|-------|
| User id | Favoriting user | `favorites.user_id` (name TBD) | FK | NOT NULL | |
| Place id | Saved place | `favorites.destination_id` (name TBD) | FK | NOT NULL | Becomes `app_places.id`. |

**Open questions:** Exact column names.

---

## `reviews` (carry-forward, remap FK)

| field | meaning | source | recommended_type | required | notes |
|--------|---------|--------|------------------|----------|-------|
| Review id | PK | `reviews` | `BIGINT` | NOT NULL | |
| Place id | Target place | `reviews` | FK | NOT NULL | Map to `app_places.id`. |
| User id | Author | `reviews` | FK | NOT NULL | |
| Rating | Star value | `reviews` | `DECIMAL` / `TINYINT` | NOT NULL | Feeds app rating. |
| Text / images | Content | `reviews` | `TEXT` / JSON | NULL | `images_json` per audit patterns. |

**Open questions:** Optional `review_images` normalization (future).

---

## `itineraries` / `itinerary_days` / `itinerary_items`

| table | field concept | source | notes |
|--------|---------------|--------|-------|
| `itineraries` | Header, user, title, dates | `itineraries` | Carry-forward. |
| `itinerary_days` | Day index, parent itinerary | `itinerary_days` | Carry-forward. |
| `itinerary_items` | Slot referencing place | `itinerary_items` | FK to place becomes `app_places.id`. |

**Open questions:** Column names for place reference and AI payload fields if any.

---

## `priority_place_tiers` (legacy / ops)

| field | meaning | source | recommended_type | required | notes |
|--------|---------|--------|------------------|----------|-------|
| (structure) | Tier / seed per audit | `priority_place_tiers` | per dump | | Not column-listed in audit. |

**Open questions:** Rename vs keep; merge into app/RAG later.

---

## Legacy mirrors (validation phase)

During parity, compare against:

- `destinations` ↔ `app_places`
- `rag_places` ↔ `rag_knowledge_base`
- `destination_images` ↔ `place_images`

See `OLD_TO_NEW_MAPPING.md` for rules.
