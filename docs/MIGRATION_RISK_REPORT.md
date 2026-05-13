# V2 Migration Risk Report

Scope: risks and safe migration plan for rebuilding the UNUtrip database.

## High-Risk Areas

### ID and relationship breakage

Current Android and Node flows use numeric `destinations.id`. RAG and AI flows often use `rag_places.place_id` / `rawPlaceId`, then map to `destination_id`.

Risk: changing ids without a reliable map will break favorites, reviews, itineraries, and AI itinerary saves.

Mitigation:

- Create a `place_id_map` during migration.
- Preserve old `destinations.id`, old `destinations.rag_place_id`, old `rag_places.place_id`, and new `app_places.id`.
- Validate every current `rag_places.destination_id` resolves to an app place.

### App/RAG taxonomy conflict

Current `destinations.category` is app-facing, while `rag_places.category_main/category_sub` is richer and language-mixed.

Risk: app filters become inconsistent if detailed RAG categories are pushed into `app_places`.

Mitigation:

- Keep app categories controlled in `app_places.category`.
- Move detailed taxonomy to `rag_knowledge_base`.
- Run an audit for categories outside the accepted app list.

### Image duplication and broken URLs

Images exist in `destination_images`, `destinations.images_json`, local webp folders, candidate CSVs, and archives.

Risk: app cards lose images or show stale external links after migration.

Mitigation:

- Prefer active `destination_images`.
- Backfill only missing approved images from `destinations.images_json`.
- Verify local `/images/destinations/...` files exist.
- Preserve image source/license metadata.

### Rating semantics

Some scripts boosted `destinations.rating` and `rag_places.quality_score` together, while the cleanup script says app rating should come from real reviews only.

Risk: app ranking mixes user review rating with AI curation quality.

Mitigation:

- `app_places.rating` = aggregate from `reviews`.
- `rag_knowledge_base.quality_score` = curation/retrieval quality.
- Do not use RAG quality score as app star rating.

### Stale SQL files

`backend/nodejs/database.sql` is older than `unudata-v2.sql`.

Risk: rebuilding from the wrong SQL file omits `rag_places`, `destination_images`, and newer fields.

Mitigation:

- Treat `unudata-v2.sql` as the primary current DB snapshot.
- Treat `backend/nodejs/database.sql` as legacy reference only.
- Generate future schema from v2 design after audit approval, not from the old Node SQL file.

### Sensitive/test user data

`unudata-v2.sql` includes users, password hashes, phone numbers, favorites, reviews, and itineraries.

Risk: copying all rows to v2 may carry demo/test personal data into production-like environments.

Mitigation:

- Classify user data separately from place data.
- Decide whether v2 starts with clean users or migrated users.
- If migrated, hash handling and privacy review must be explicit.

## Safe V2 Migration Plan

### Phase 0: Freeze and snapshot

- Stop ad hoc edits to Excel, SQL, JSON, and image CSVs during migration.
- Take a fresh MySQL dump of current `unudata`.
- Snapshot `backend/nodejs/public/images/destinations`.
- Record checksums or file counts for key inputs.

### Phase 1: Build migration inventory

- Use `unudata-v2.sql` or a live DB snapshot as primary input.
- Load current `destinations`, `rag_places`, `destination_images`, `reviews`, `favorites`, and itinerary tables into a staging environment.
- Build `place_id_map` from:
  - old `destinations.id`
  - old `destinations.rag_place_id`
  - old `rag_places.place_id`
  - old `rag_places.destination_id`
  - image folder names where possible

### Phase 2: Create clean staging models

- Populate staging `app_places` from current `destinations`.
- Populate staging `rag_knowledge_base` from current `rag_places` and `places_rag_documents.jsonl`.
- Populate staging `place_images` from active `destination_images`.
- Backfill missing images from `destinations.images_json`.
- Keep `destination_image_candidates` outside runtime unless image curation is needed.

### Phase 3: Validate before SQL generation

Required checks:

- Count of active `app_places` equals expected active `destinations`.
- Every `rag_knowledge_base.app_place_id` that should link does link.
- Every favorite/review/itinerary item maps to a valid `app_places.id`.
- Every active `place_images` local URL has a real file.
- No app category outside the approved app list.
- No `app_places.rating` comes from RAG quality score.
- Android API response can still produce the current `Destination` fields.

### Phase 4: Generate v2 SQL only after signoff

- Generate schema SQL.
- Generate data migration SQL or scripts.
- Run in a disposable local database first.
- Export validation reports.
- Do not delete old tables until v2 app/backend/RAG are verified.

### Phase 5: Parallel run

- Run old and v2 databases side by side.
- Point a staging backend to v2.
- Verify Android destination list, detail, nearby, favorites, reviews, chatbot, and AI itinerary creation.
- Compare RAG retrieval answers for known test prompts from archived reports.

### Phase 6: Cutover and rollback

- Cut over only after staging parity checks pass.
- Keep old dump, old image folder, and id map immutable.
- Rollback plan: restore old DB and point backend back to `unudata`.

## Data Quality Checks To Add

- Duplicate place names within same province/area.
- `destinations.id` vs `rag_places.destination_id` one-to-one integrity.
- Places with no image and high priority.
- Places with image rows but no active app place.
- RAG records with no `search_text`.
- App places with null coordinates.
- App places with empty description.
- Categories outside approved list.
- External image URLs that are dead or redirect to non-image content.

## Recommendation

Proceed with v2 as a staged rebuild. Do not mutate current tables directly. The safest path is to produce a clean v2 schema and migration pipeline after this audit, run it into a new database, validate behavior, then cut over only when Node, Android, and FastAPI RAG all pass parity tests.
