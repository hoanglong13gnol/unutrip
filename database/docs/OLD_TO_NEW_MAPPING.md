# Old-to-New Mapping (V2)

**Scope:** Documentation only. Describes how rows in the current primary database snapshot (`unudata-v2.sql` / live `unudata`) conceptually map to v2 tables.  
**Legacy reference only:** `backend/nodejs/database.sql` (older, missing RAG/image tables per audit).

---

## Global rules

1. **Primary source:** `unudata-v2.sql` and/or live DB `unudata`.
2. **Mandatory `place_id_map`:** Every migrated `app_places` row should have a map entry. In first cut, `old_destination_id` and `new_app_place_id` are the same numeric value; the map is still required for `rag_place_id`, `rag_places.place_id`, `rawPlaceId`, image folder keys, and `place_key`.
3. **Ratings:** `app_places.rating` and `review_count` come from aggregates over `reviews` only—not from `rag_places.quality_score` or ad-hoc boosts (risk report).
4. **RAG quality:** `quality_score` lives only under `rag_knowledge_base` (or interim legacy `rag_places` until cutover).
5. **No legacy drops:** `destinations`, `rag_places`, `destination_images`, and other existing tables stay until v2 parity passes.

---

## `destinations` → `app_places`

| New field (concept) | Old source | Rule / notes |
|---------------------|------------|--------------|
| `id` | `destinations.id` | **Direct reuse required in first cut:** `app_places.id = destinations.id` (no numeric remap). |
| `place_key` | `destinations.rag_place_id` preferred | Direction: base on `rag_place_id` / `place_id` where possible. If null, **open question**: generate new key vs use slug heuristic. |
| `name`, `description`, `short_description`, `address`, `city`, `province`, `area` | same-named columns | Direct copy. |
| `latitude`, `longitude` | same | Direct copy. |
| `category` | `destinations.category` | Normalize to app controlled list; audit: categories outside list need remediation. |
| `open_time`, `close_time`, `entry_fee` | same | Direct copy. |
| `budget_level`, `walking_level`, `kid_friendly`, `elderly_friendly`, `recommended_use`, `tags_json` | same | Direct copy. |
| `is_active` | `destinations.is_active` | Direct copy. |
| Timestamps | `destinations` | Copy if columns exist. |
| `primary_image_url` | derive | After `place_images` populated: URL where `is_primary` and active; else from legacy `images_json` primary. Denormalized. |
| `rating`, `review_count` | **not** from `destinations.rating` as authority | Recompute from `reviews` for linked `app_place_id`. Numeric ids are reused; `place_id_map` still supports cross-key linkage. |

**Do not map into `app_places` (stay in RAG or supporting tables):**

- Heavy RAG text (`search_text`), `raw_json`-class payloads.
- Detailed RAG taxonomy unless product decides app needs it (direction: detailed taxonomy primarily in `rag_knowledge_base`).

**Open questions:**

- Fate of `destinations.images_json`, `image_source`, `image_credit` at row level vs only in `place_images`.
- Fate of `destinations.category_main` / `category_sub` (audit: duplicates / conflicts with `rag_places`).

---

## `rag_places` + `places_rag_documents.jsonl` → `rag_knowledge_base`

| New field (concept) | Old / file source | Rule / notes |
|---------------------|-------------------|--------------|
| Core text & metadata | `rag_places` columns | Map per `V2_SCHEMA_DESIGN.md` / dictionary. |
| `place_key` | `rag_places.place_id` | Align with `app_places.place_key` when they match. |
| `app_place_id` | `rag_places.destination_id` | Resolve via `place_id_map.old_destination_id` → `new_app_place_id`. |
| `knowledge_type` | default `place` | JSONL docs may set other types—**open question**. |
| JSONL documents | `backend/rag/data/processed/places_rag_documents.jsonl` | Each line becomes or merges into `rag_knowledge_base` row(s); merge vs many-rows **open question**. |
| `quality_score` | `rag_places.quality_score` only | Never map to `app_places.rating`. |
| `raw_json` | `rag_places.raw_json` | Carry to `raw_json` / `source_payload_json`. |

**Open questions:**

- **Cardinality:** One `rag_knowledge_base` row per `rag_places` row plus separate rows per JSONL doc vs consolidation.
- **Keys in JSONL:** Which field is `knowledge_key` (not in authorized docs).
- Records in `rag_places` with null `destination_id` or mismatched ids—exception handling in map.

---

## `destination_images` (+ `destinations.images_json`) → `place_images`

| New field | Old source | Rule |
|-----------|------------|------|
| `app_place_id` | `destination_images.destination_id` | Map through `place_id_map` to `app_places.id`. |
| `place_key` | `destination_images.rag_place_id` or from `app_places` | Copy if present. |
| `image_url` | `destination_images.image_url` | Primary. |
| `source`, `credit`, `license_note`, `is_primary`, `status` | `destination_images` | Direct copy. |
| `source_page_url`, `sort_order` | `destination_images` if columns exist; else `images_json` objects | Image audit: not all detail in `destination_images`. |
| Backfill | `destinations.images_json` | Use only where no suitable active `destination_images` row; parse strings vs objects (mixed formats per audit). |

**Open questions:**

- Promotion rules for `status` values.
- Whether local files without DB rows get inserted from disk scan (not specified in authorized docs).

---

## `destination_image_candidates` → `place_image_candidates`

- Structural copy with optional rename (direction).
- Remap any `destination_id` to `app_place_id` using `place_id_map`.

**Open questions:** Exact column mapping list from dump.

---

## `priority_place_tiers` → (no mandatory v2 rename in docs)

- Remains legacy until fold/renamed per product decision.

**Open questions:** Target v2 name and FK to `app_places` if any.

---

## User product tables: FK remaps

### `favorites`

- Identify column holding `destinations.id` (audit: favorites reference destinations).
- Keep numeric target id value unchanged in first cut (`destinations.id` reused as `app_places.id`); validate via `place_id_map`.

### `reviews`

- Keep destination reference value unchanged in first cut (`app_places.id = destinations.id`), with `place_id_map` for audit and cross-key mapping.
- Recompute `app_places.rating` / `review_count` from all reviews for that id.

### `itinerary_items`

- Keep destination/place reference value unchanged in first cut (`app_places.id = destinations.id`), with `place_id_map` validation.
- Preserve order fields and day linkage as-is (names in dump not expanded here).

**Open questions:** Exact column names in `favorites`, `reviews`, `itinerary_items`.

---

## AI / RAG id path (behavioral mapping)

**Today (audit):** RAG/AI responses may carry `rawPlaceId` / `place_id`; Node resolves via `rag_places.place_id` → `rag_places.destination_id` → `destinations.id`.

**V2 target (documentation):**

- Resolve `place_key` / RAG id through `place_id_map` and/or `rag_knowledge_base.app_place_id`.
- No change to application code in this phase—mapping is the data contract goal.

**Open questions:** Whether `rag_knowledge_base` keeps duplicate lookup by old `place_id` string without map row.

---

## Image filesystem ↔ database

- Public webp tree: `backend/nodejs/public/images/destinations/` (served as `/images/destinations/...` per audit).
- DB URLs may use `rag_place_id`-style folder or slug folder; audit notes inconsistency.
- **Mapping:** `place_id_map.image_folder_key` may capture folder name when known—optional, per schema design.

**Open questions:** Automated reconciliation of folder names to `place_key`.

---

## Reference file roles (not SQL tables)

Per `docs/DATA_INVENTORY.md`:

- `backend/rag/data/processed/places_app_reviewed.json` — reviewed app source before DB import (audit).
- Excel, CSV pipelines — operational inputs; not runtime after cutover (direction).

These inform **validation and manual fixes**, not automatic row mapping unless explicit migration batching is defined later.

**Open questions:** Which batches are authoritative for conflict resolution when SQL dump disagrees with JSON.

---

## Summary matrix

| Legacy artifact | v2 primary target |
|-----------------|-------------------|
| `destinations` | `app_places` |
| `rag_places` | `rag_knowledge_base` (in part) |
| `places_rag_documents.jsonl` | `rag_knowledge_base` |
| `destination_images` | `place_images` |
| `destinations.images_json` | `place_images` (backfill) |
| `destination_image_candidates` | `place_image_candidates` (optional rename) |
| `favorites`, `reviews`, `itinerary_items` (place FK) | same tables, FK → `app_places.id` |
| All id forms | `place_id_map` |
