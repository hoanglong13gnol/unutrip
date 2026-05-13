# V2 Database Direction

Goal: rebuild the UNUtrip database around two main data tables, with supporting tables only where they protect product behavior or data quality.

## Architectural Direction

Use two main place/knowledge tables:

- `app_places`: structured, stable, API-friendly data for Android and app UI.
- `rag_knowledge_base`: textual and retrieval-oriented knowledge for backend AI/RAG.

Keep user-generated product data and media metadata in supporting tables.

## `app_places`

Purpose: the app contract. It should contain only fields the Android app, Node API, map/search flows, favorites, reviews, and itinerary runtime need.

Recommended fields:

- `id`: numeric app place id.
- `place_key`: stable shared key, based on current `rag_place_id/place_id` where possible.
- `name`
- `description`
- `short_description`
- `address`
- `city`
- `province`
- `area`
- `latitude`
- `longitude`
- `category`: canonical app category code.
- `open_time`
- `close_time`
- `entry_fee`
- `budget_level`
- `walking_level`
- `kid_friendly`
- `elderly_friendly`
- `recommended_use`
- `tags_json`
- `primary_image_url`: optional denormalized convenience field.
- `rating`
- `review_count`
- `is_active`
- timestamps

Data that should become `app_places`:

- Current `destinations` fields used by Android models and Node DTOs.
- Canonical app category values from `destinations.category`.
- Clean location, geo, practical info, and display tags.
- Review-derived `rating` and `review_count`, not AI quality score.
- One stable `place_key` to link RAG, images, and old ids.

Data that should not be in `app_places`:

- Full RAG prompt/search text.
- Raw JSON payloads.
- Candidate image review data.
- Detailed RAG taxonomy if it is not used by app filters.
- AI scoring fields that do not directly affect app UI.

## `rag_knowledge_base`

Purpose: AI retrieval and answer grounding. It can be place-centric at first, but should be modeled as knowledge records, not app cards.

Recommended fields:

- `id`
- `knowledge_key`: stable id for the knowledge record.
- `place_key`: nullable link to `app_places.place_key`.
- `app_place_id`: nullable FK to `app_places.id`.
- `title`
- `knowledge_type`: `place`, `itinerary`, `constraint`, `policy`, `local_tip`, etc.
- `content`
- `summary`
- `province`, `city`, `area`
- `category_main`, `category_sub`
- `tags_json`, `interest_tags_json`
- `suitable_for_json`, `avoid_for_json`
- `budget_level`, `walking_level`, `activity_level`
- `kid_friendly`, `elderly_friendly`
- `best_time_of_day_json`, `slot`, `duration_minutes`
- `quality_score`
- `recommended_use`
- `must_not_schedule_as_main`
- `requires_realtime_check`
- `realtime_fields_json`
- `source`, `source_url`, `last_updated`
- `embedding_status` or `index_status`
- `search_text`
- `raw_json` or `source_payload_json`
- `is_active`
- timestamps

Data that should become `rag_knowledge_base`:

- Current `rag_places` text, normalized filters, scheduling hints, suitability/avoidance fields, source metadata, and raw payload.
- Current `places_rag_documents.jsonl` document text and doc types.
- RAG-specific fields from processed JSON files that are not needed by Android.
- Itinerary/constraint documents if they are used by retriever and prompt builder.

## Supporting Tables Actually Needed

Keep:

- `users`: auth/profile/preferences.
- `favorites`: many-to-many users and `app_places`.
- `reviews`: user review text/rating for `app_places`.
- `review_images`: optional normalized replacement for review `images_json`.
- `itineraries`: user itinerary headers.
- `itinerary_days`: days under an itinerary.
- `itinerary_items`: ordered scheduled `app_places`.
- `place_images`: approved image list for `app_places`.
- `place_image_candidates`: optional operational staging table for image curation.
- `place_aliases`: optional if search/name dedupe remains important.
- `place_taxonomy`: optional if categories need labels, ordering, icons, and app filter governance.
- `place_id_map`: strongly recommended during migration to preserve old `destinations.id`, old `rag_places.place_id`, slug folders, and new ids.
- `data_import_batches`: recommended for auditability of imports from Excel/JSON/SQL/CSV.

Probably do not keep as runtime tables:

- `priority_place_tiers` as-is. Fold into `app_places.recommended_use`, `rag_knowledge_base.quality_score`, or a curation table if the process remains active.
- `destination_image_candidates` in production app runtime. Keep only as staging/ops if image collection continues.
- Backup tables created by scripts. Export/archive them outside runtime schema.

## Category Direction

The app should use a small controlled category list:

- `beach`
- `mountain`
- `city`
- `heritage`
- `nature`
- `checkin`
- `food`
- `culture`
- `religious`

Detailed taxonomy belongs in `rag_knowledge_base.category_main/category_sub`, not in app filters unless a user-facing feature needs it.

## Image Direction

- Use `place_images` as the source of truth for approved images.
- Keep `app_places.primary_image_url` only as a denormalized field if needed for performance.
- Preserve image provenance and license fields in `place_images`.
- Continue serving local files from `/images/destinations/...`, but key them by stable `place_key`.

## API Compatibility Direction

The current Android model expects fields equivalent to:

- `id`, `name`, `description`, `address`, `city`, `province`, `latitude`, `longitude`
- `category`, `images`, `rating`, `reviewCount`
- `openTime`, `closeTime`, `entryFee`, `tags`, `isFavorite`, `distanceKm`

V2 should either keep the API response shape stable or update Android after the database migration is validated.

## Recommended First V2 Cut

Build v2 as a clean replacement, not as layers of compatibility tables:

- `app_places` from current `destinations`.
- `rag_knowledge_base` from current `rag_places` plus RAG JSONL documents.
- `place_images` from current `destination_images`, backfilled from `destinations.images_json`.
- Preserve old-to-new ids in `place_id_map`.
- Keep user/review/favorite/itinerary tables and remap them to `app_places.id`.
