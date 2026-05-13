# V2 Validation Checklist (Documentation Only)

Use this checklist before generating migration SQL, cutting over traffic, or dropping/retiring legacy tables.  
**Policy:** Legacy tables (e.g. `destinations`, `rag_places`, `destination_images`) **remain** until all applicable items pass.

Sources: `docs/MIGRATION_RISK_REPORT.md`, `docs/CURRENT_DATABASE_AUDIT.md`, `docs/IMAGE_DATA_AUDIT.md`, `docs/V2_DATABASE_DIRECTION.md`, `docs/DATA_INVENTORY.md`.

---

## A. Snapshot and freeze (Phase 0)

- [ ] Fresh MySQL dump of current `unudata` captured (or `unudata-v2.sql` confirmed current).
- [ ] Snapshot of `backend/nodejs/public/images/destinations/` taken (count / checksum per ops standard).
- [ ] Inputs freeze agreed: ad hoc edits to Excel, JSON, CSV, and SQL paused for the migration window (risk report).
- [ ] `backend/nodejs/database.sql` **not** used as primary schema truth (reference only).

---

## B. `place_id_map` and identifier integrity

- [ ] `place_id_map` exists and is populated for all migrated `app_places` rows intended to have legacy lineage.
- [ ] **First-cut id lock:** `app_places.id` reuses `destinations.id` exactly (no numeric id reassignment).
- [ ] Every **old** `destinations.id` that still has product references appears in the map (favorites, reviews, itinerary items).
- [ ] Every **current** `rag_places.destination_id` that should link resolves to an `app_places.id` (risk report).
- [ ] **Open validation:** `destinations.id` ↔ `rag_places.destination_id` cardinality checked (audit raised 1:1 expectation—confirm or document exceptions).
- [ ] **Open validation:** Collisions on `rag_places.place_id` / `place_key` identified and reconciled.

---

## C. `app_places` parity

- [ ] Count of **active** `app_places` matches expected **active** `destinations` (risk report).
- [ ] No app **`category`** outside the approved controlled list (direction + risk report); exceptions documented with remediation.
- [ ] **No null coordinates** where product requires map/nearby (audit suggested DQ check—confirm product rule).
- [ ] **Empty description** spots flagged if business requires non-empty descriptions (risk report DQ ideas).
- [ ] **Duplicate place names** within same province/area reviewed (risk report).

---

## D. Ratings and reviews

- [ ] **`app_places.rating` and `review_count` match aggregates from `reviews`** after FK remap; not copied from RAG `quality_score`.
- [ ] Spot check: legacy `destinations.rating` divergences explained (historic boosts per risk report).
- [ ] **Sensitive / test user data** handling decided: migrate vs clean room (risk report).

---

## E. `rag_knowledge_base`

- [ ] Rows sourced from **`rag_places`** with fields mapped per dictionary.
- [ ] JSONL ingestion (`places_rag_documents.jsonl`) completed per agreed merge rules (**open** until JSONL schema documented).
- [ ] **`quality_score`** present only on `rag_knowledge_base` / legacy `rag_places`—**not** on `app_places.rating`.
- [ ] Records missing **`search_text`** or equivalent retrieval field flagged (risk report).
- [ ] `raw_json` / large payloads accounted for (storage / performance awareness per audit).

---

## F. Images (`place_images`)

- [ ] **Primary path:** active `destination_images` migrated to `place_images` before bulk `images_json` backfill.
- [ ] **`images_json` backfill** only fills gaps; mixed string/object formats handled.
- [ ] For each `/images/destinations/...` URL, **file exists** on disk or issue logged (risk + image audit).
- [ ] **Primary image** integrity: at most one logical primary per place under defined rule—exceptions listed.
- [ ] **`app_places.primary_image_url`** matches chosen primary from `place_images` when populated.
- [ ] **Dead or misleading external URLs** flagged (risk report DQ).

---

## G. Product graph (favorites, itineraries)

- [ ] **`favorites`** references resolve to valid `app_places.id` with unchanged numeric ids in first cut.
- [ ] **`itinerary_items`** (and related) references resolve to valid `app_places.id` with unchanged numeric ids in first cut.
- [ ] **AI itinerary save path:** `rawPlaceId` / `place_id` still resolves through **`place_id_map`** / knowledge linkage in staging (behavior parity—requires app/backend test, not DB-only).

---

## H. RAG / API parity (staging)

- [ ] Staging backend pointed at v2 DB: destination/place list, detail, nearby behave for Android-equivalent API contract (direction).
- [ ] Chatbot / RAG retrieval smoke tests against known prompts (risk report Phase 5).
- [ ] Readiness paths unaffected: file indexes present where required (README notes `bm25_index.pkl`); **coordination with ops** if DB export feeds index rebuild (**open question**).

---

## I. Legacy coexistence

- [ ] **No legacy tables dropped** until A–H pass and sign-off recorded.
- [ ] **Parallel run** completed if required by release policy (risk report Phase 5).
- [ ] Rollback plan documented: restore prior DB + revert backend pointer (risk report Phase 6).

---

## J. Optional / future validation

Track only if corresponding tables exist in v2 cut:

- [ ] `place_image_candidates` workflow still meets ops needs.
- [ ] `priority_place_tiers` behavior if folded or renamed.
- [ ] `review_images` if review attachments normalized.
- [ ] `data_import_batches` if batch provenance required.

---

## Sign-off block

| Role | Name | Date | Notes |
|------|------|------|-------|
| Data / DBA | | | |
| Backend | | | |
| Android | | | |
| RAG | | | |

---

## Open dependencies (not gateable until documented)

- JSONL schema for `places_rag_documents.jsonl`.
- Exact `destination_images.status` semantics.
- `place_id_map` population rules for non-numeric key collisions (`rag_place_id`, `place_id`, folder keys).
