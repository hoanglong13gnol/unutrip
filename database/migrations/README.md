## Database migrations (v2 refactor)

### Scope of this folder (current phase)

- **Schema migrations only**: create v2 tables and v2-only indexes.
- **No data migration** in these files.
- **No destructive operations**: do not drop tables, do not drop indexes, and do not alter legacy tables.

### Migration order

Apply in numeric order:

- `001_create_app_places.sql`
- `002_create_rag_knowledge_base.sql`
- `003_create_place_images.sql`
- `004_create_place_id_map.sql`
- `005_create_v2_indexes.sql`

### Locked decisions (implemented by schema shape)

- **`app_places.id` reuses `destinations.id`** in the first cut (no new ids generated in schema migrations).
- **`place_key` storage** exists on `app_places` and is mapped via `place_id_map` (actual population is a later data migration).
- **`place_id_map` cardinality**: do **not** assume one app place has only one legacy/RAG key; the mapping may be **multiple rows per `app_places.id`**.
- **RAG first cut**: `rag_places` is the primary source for `rag_knowledge_base` (ingestion of `places_rag_documents.jsonl` is deferred).
- **`rag_places.last_updated`** stays **VARCHAR-compatible text** in the first migration (mirrored by `rag_knowledge_base.last_updated`).
- **Images**: runtime `place_images` will only accept rows sourced from legacy `destination_images.status = active` during a later data migration.

### Notes on index migration compatibility

- MySQL does not reliably support `CREATE INDEX IF NOT EXISTS`.
- `005_create_v2_indexes.sql` uses **information_schema guards + dynamic SQL** to add indexes only when missing (safe to re-run).

