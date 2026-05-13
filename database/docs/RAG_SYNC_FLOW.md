# RAG ↔ Database Sync Flow (Documentation Only)

**Goal:** Describe how **retrieval knowledge** is represented in v2 (`rag_knowledge_base`) and how it **originates from** current `rag_places`, `places_rag_documents.jsonl`, and related inputs—without changing RAG or backend code in this phase.

**Confirmed split:**

- **`app_places`:** Android / API / structured UI contract.
- **`rag_knowledge_base`:** Backend / RAG / AI grounding and retrieval-oriented fields.

**Confirmed constraints:**

- **`quality_score`** belongs only in **`rag_knowledge_base`** (and legacy `rag_places` until cutover). It **must not** drive **`app_places.rating`** (risk report / user decision).
- App **`rating`** aggregates come from **`reviews`** only.

---

## Source artifacts

| Artifact | Location / table | Role |
|----------|------------------|------|
| `rag_places` | `unudata-v2.sql` / live DB | Current wide “place knowledge” table: text, `search_text`, taxonomy, scheduling hints, `quality_score`, `raw_json`, linkage `place_id` / `destination_id`. |
| `places_rag_documents.jsonl` | `backend/rag/data/processed/places_rag_documents.jsonl` | RAG document corpus for retrieval (per data inventory). |
| RAG runtime indexes | e.g. `data/indexes/bm25_index.pkl` (per README) | File-based; not DB tables. |

Other processed JSON/Excel paths exist in inventory; they are **optional migration inputs** unless a future batch marks them authoritative (**open question**).

---

## Target: `rag_knowledge_base`

**Purpose:** Single logical table for **knowledge records** consumed when building retrievers, prompts, and admin/debug flows—aligned with `docs/V2_DATABASE_DIRECTION.md`.

**Key linkage fields (conceptual):**

| Field | Purpose |
|--------|---------|
| `knowledge_key` | Stable identifier per knowledge row / document. |
| `place_key` | Joins to `app_places.place_key` when the record is place-associated. |
| `app_place_id` | Optional FK to `app_places.id` for strict relational joins. |
| `knowledge_type` | Distinguishes place vs itinerary vs constraint docs, etc. (exact enum **open question**). |

---

## Flow: existing DB (`rag_places`) → `rag_knowledge_base`

**Intended mapping (high level):**

1. For each `rag_places` row, create (at least) one `rag_knowledge_base` record of `knowledge_type = 'place'` (**default label**; confirm naming).
2. Copy textual and filter fields per `V2_SCHEMA_DESIGN.md` / `TABLE_FIELD_DICTIONARY.md`.
3. **`quality_score`:** from `rag_places.quality_score` only into **`rag_knowledge_base.quality_score`**.
4. **`raw_json` / `search_text`:** preserve for audit and retrieval (size caveat in audit).
5. **`app_place_id`:** resolve `rag_places.destination_id` through **`place_id_map`** to `app_places.id`.
6. **`place_key`:** prefer `rag_places.place_id` string aligned with `app_places.place_key` when consistent.

**Open questions:**

- One-to-one `rag_places` ↔ `rag_knowledge_base` or split into multiple knowledge rows (e.g. separate scheduling snippet).
- Handling rows where `destination_id` is missing or orphaned.
- Normalization of `category_main` / `category_sub` vs controlled `app_places.category`.

---

## Flow: JSONL (`places_rag_documents.jsonl`) → `rag_knowledge_base`

**Intended flow (documentation level):**

1. Read each JSONL line as a **document** candidate.
2. Assign `knowledge_key` from a field in the JSONL line if present; otherwise generate (**open question**: key format).
3. Set `knowledge_type` from doc metadata if present (inventory does not list fields here).
4. Map body text into `content` / `search_text` / `summary` per conventions to be fixed when JSONL schema is available (**open question**).
5. Link to `app_place_id` / `place_key` using ids present in the JSONL line or via join to `rag_places` / `place_id_map` (**open question**).

**Open questions:**

- Merge lines for the same place vs keep all lines as separate retrievable docs.
- How JSONL-only docs relate to existing `rag_places` rows (duplicate vs supplement vs replace).

---

## Flow: RAG runtime build (conceptual)

The FastAPI service today is **file/index-oriented** (README); DB tables support scripts and linkage.

**Documented intent after v2 (no implementation here):**

1. **Ingest:** MySQL `rag_knowledge_base` rows (+ optional files) feed export/build steps that regenerate BM25 / hybrid artifacts.
2. **Linkage:** Retriever uses `knowledge_key` / content; orchestration may still receive **`rawPlaceId`** / `place_id` from models—resolved via **`place_id_map`** and `app_places` during itinerary save and mapping (per current Node audit).

**Open questions:**

- Whether `embedding_status` / `index_status` are stored in MySQL or only inferred from filesystem.
- Cadence: online refresh vs batch export from DB.

---

## Separation from app surface

**Must remain true:**

| Concern | Lives in |
|---------|----------|
| Star rating for UI | `app_places` from `reviews` |
| Curation / retrieval quality | `rag_knowledge_base.quality_score` |
| Card title, short listing fields | `app_places` |
| Long grounding text, `raw_json`, BM25 text | `rag_knowledge_base` |

**Risk:** Historic scripts allegedly boosted `destinations.rating` using priority or quality—**must not** carry forward into v2 app rating (risk report).

---

## `place_id_map` role in RAG sync

- Ensures every resolvable `rag_places.destination_id` maps to exactly one `app_places.id` for FK population.
- Stores `rag_places.place_id` for lookup paths that bypass numeric destination id.

**Open questions:**

- Multiple `rag_places` rows pointing at same `destination_id`—whether allowed and how to choose primary link for `app_place_id` on a knowledge row.

---

## Taxonomy

- **App filters:** controlled `app_places.category` list (direction doc).
- **Detailed taxonomy:** `rag_knowledge_base.category_main` / `category_sub` from `rag_places` and possibly JSONL—**must not** leak into app unless product explicitly exposes it.

**Open questions:** Audit process for categories outside app list (risk report).

---

## Validation ties

See **`VALIDATION_CHECKLIST.md`:** e.g. RAG records missing `search_text`, linkage completeness, retrieval regression in staging (risk report Phase 5).

---

## Open questions (consolidated)

1. JSONL record schema (field names, types).
2. Cardinality: JSONL docs vs `rag_places` rows vs merged knowledge rows.
3. `knowledge_type` enum and mandatory fields per type.
4. Handling non-place documents (policies, constraints) if present in JSONL.
5. Index rebuild ownership (ops runbook vs app automation).
6. Whether `rag_knowledge_base` replaces all reads of `rag_places` on day one or runs in parallel until parity.
