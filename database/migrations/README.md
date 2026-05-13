## Database migrations (v2 refactor)

### Scope of this folder (current phase)

- **Schema migrations (`001`-`005`)**: create v2 tables and v2-only indexes.
- **Data population migrations (`006`-`009`)**: populate v2 tables from legacy sources.
- **Validation (`010`)**: read-only SELECT checks for migration parity and rule compliance.
- **No destructive operations**: do not drop tables, do not drop indexes, and do not alter legacy tables.
- Test these migrations on `unudata_v2_test` first before production use.

### Migration order

Apply in numeric order:

- `001_create_app_places.sql`
- `002_create_rag_knowledge_base.sql`
- `003_create_place_images.sql`
- `004_create_place_id_map.sql`
- `005_create_v2_indexes.sql`
- `006_populate_app_places.sql`
- `007_populate_place_id_map.sql`
- `008_populate_place_images.sql`
- `009_populate_rag_knowledge_base.sql`
- `010_v2_validation_queries.sql`

### Locked decisions (implemented by schema shape)

- **`app_places.id` reuses `destinations.id`** in the first cut (no new ids generated in schema migrations).
- **`place_key` storage** exists on `app_places` and is mapped via `place_id_map` (population implemented in data migrations).
- **`place_id_map` cardinality**: do **not** assume one app place has only one legacy/RAG key; the mapping may be **multiple rows per `app_places.id`**.
- **RAG first cut**: `rag_places` is the primary source for `rag_knowledge_base` (ingestion of `places_rag_documents.jsonl` is deferred).
- **`rag_places.last_updated`** stays **VARCHAR-compatible text** in the first migration (mirrored by `rag_knowledge_base.last_updated`).
- **Images**: runtime `place_images` accepts rows sourced from legacy `destination_images.status = active`.

### Notes on index migration compatibility

- MySQL does not reliably support `CREATE INDEX IF NOT EXISTS`.
- `005_create_v2_indexes.sql` uses **information_schema guards + dynamic SQL** to add indexes only when missing (safe to re-run).

