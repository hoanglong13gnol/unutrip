# Current Database Audit

Scope: current MySQL/MariaDB usage found in SQL dumps, Node backend, and RAG scripts.

## Database Connections

- Node backend uses MySQL through `mysql2/promise` in `backend/nodejs/src/db.js`.
- Default database name is `unudata`.
- `migrate()` in Node is intentionally skipped; schema is managed by dump/import scripts.
- FastAPI RAG runtime is file/index based, but RAG scripts import/export MySQL data for `destinations`, `rag_places`, and image tables.

## SQL Dump Comparison

`backend/nodejs/database.sql` is the older app schema:

- `users`
- `destinations`
- `favorites`
- `reviews`
- `itineraries`
- `itinerary_days`
- `itinerary_items`

`unudata-v2.sql` is the current richer dump:

- `destinations`
- `destination_images`
- `destination_image_candidates`
- `favorites`
- `itineraries`
- `itinerary_days`
- `itinerary_items`
- `priority_place_tiers`
- `rag_places`
- `reviews`
- `users`

The current code already references `rag_places` and `destination_images`, so `backend/nodejs/database.sql` is not sufficient for current runtime behavior.

## Current Tables And Purpose

### `destinations`

Purpose: app-facing destination table for Android lists, detail screens, maps, nearby search, favorites, reviews, and itinerary items.

Current fields include:

- Identity/linking: `id`, `rag_place_id`
- UI basics: `name`, `description`, `short_description`, `address`, `city`, `province`, `area`
- Geo/search: `latitude`, `longitude`
- App taxonomy: `category`, `category_main`, `category_sub`
- Images: `images_json`, `image_source`, `image_credit`
- Display/ranking: `rating`, `review_count`
- Practical info: `open_time`, `close_time`, `entry_fee`
- UI filters: `budget_level`, `walking_level`, `kid_friendly`, `elderly_friendly`, `recommended_use`
- Metadata: `tags_json`, `is_active`, timestamps

Audit note: this table is doing too much. It mixes app UI fields, image metadata, RAG linkage, taxonomy cleanup state, and partly AI-oriented attributes.

### `rag_places`

Purpose: AI/RAG place knowledge table with detailed text, retrieval metadata, scheduling hints, and raw source preservation.

Current fields include:

- Linking: `place_id`, `destination_id`
- Place identity/location: `name`, aliases, `province`, `city`, `area`, group, address, coordinates
- Taxonomy: `category_main`, `category_sub`, normalized versions
- Text and retrieval: `description`, `short_description`, `search_text`, `raw_json`
- AI filters: interest/suitable/avoid JSON, walking/activity/budget normalized fields
- Scheduling: best time, slot, duration, night activity, main/supporting recommendation
- Safety/freshness: realtime flags and fields
- Quality: `quality_score`, `is_generic`, `must_not_schedule_as_main`
- Provenance: `source`, `source_url`, `last_updated`

Audit note: this table is the closest current match for the proposed `rag_knowledge_base`, but it is still place-centric and column-heavy.

### `destination_images`

Purpose: normalized active image list for app destinations. Node attaches active images from this table before falling back to `destinations.images_json`.

Fields: `id`, `destination_id`, `rag_place_id`, `image_url`, `source`, `credit`, `license_note`, `is_primary`, `status`, timestamps.

Audit note: this should remain a supporting table in v2. Keeping images normalized is safer than storing only `images_json`.

### `destination_image_candidates`

Purpose: staging/review table for image candidate collection and human/AI approval.

Fields include candidate URL, source page, provider, confidence, review notes, candidate status, and batch code.

Audit note: useful for data operations, but it should not be part of the app runtime contract.

### `priority_place_tiers`

Purpose: ranking/priority seed table for image coverage and scoring scripts.

Audit note: this is operational enrichment data. It can become `place_priority_tiers` or be folded into curated metadata if the process remains active.

### User And Transaction Tables

- `users`: authentication profile, avatar, preferences.
- `favorites`: user-to-destination saved places.
- `reviews`: user reviews and review images.
- `itineraries`: itinerary header.
- `itinerary_days`: day rows under an itinerary.
- `itinerary_items`: destination visits within itinerary days.

Audit note: these should remain separate from the two main place/knowledge tables. They are product runtime tables, not source knowledge.

## Backend Database Usage

Node routes use:

- `destinations`: app lists, featured, nearby, details, admin CRUD, AI candidate listing.
- `destination_images`: active image attachment in `helpers.attachDestinationImages`.
- `rag_places`: mapping AI `rawPlaceId/place_id` to app `destinations.id` when saving AI itineraries.
- `favorites`: favorite state and saved destinations.
- `reviews`: review create/list and aggregate rating update back to `destinations`.
- `itineraries`, `itinerary_days`, `itinerary_items`: manual and AI-created itineraries.
- `users`: auth, profile, preferences, avatar.

Critical dependency: AI-generated selections often return `rawPlaceId`, not numeric `destinationId`; Node resolves this through `rag_places.place_id -> rag_places.destination_id`.

## Current Issues

- `backend/nodejs/database.sql` is stale compared with `unudata-v2.sql`.
- Node app currently assumes `destination_images` and `rag_places` exist, but the older SQL file does not define them.
- `destinations.rating` is used by app ranking, but cleanup scripts say it should be based on real reviews only; other scripts boosted rating/quality by priority tier.
- `destinations.category_main/category_sub` duplicate or conflict with `rag_places.category_main/category_sub`.
- `destinations.images_json` and `destination_images` duplicate image lists.
- `rag_places.raw_json` preserves large source payloads inside MySQL, which is useful for audit but heavy for runtime.

## Recommended Interpretation For V2

- Rename the app-facing concept from `destinations` to `app_places` or create `app_places` as the clean v2 replacement.
- Rename/reframe `rag_places` as `rag_knowledge_base`, but keep a stable `place_id` and optional `app_place_id` link.
- Keep user, favorite, review, itinerary, image, and operational staging tables separate.
- Treat SQL dumps, Excel, JSON, and CSV as migration inputs, not runtime sources after v2 is cut over.
