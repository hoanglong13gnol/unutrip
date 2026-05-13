# Image Data Audit

Scope: current image storage, references, and risks for UNUtrip v2 database planning.

## Current Image Storage

Primary local destination image storage:

- `backend/nodejs/public/images/destinations/`
- 161 destination subfolders.
- 448 `.webp` files.
- Served by Node from `backend/nodejs/src/index.js` as `/images/...`.

Runtime upload storage:

- `backend/nodejs/uploads/reviews/`: review images uploaded by users.
- `backend/nodejs/uploads/avatars/`: user avatar uploads.
- Served by Node as `/uploads/...`.

Android app resources:

- `app/src/main/res/drawable/bg_auth_hero.png`
- `app/src/main/res/drawable/ic_edit.png`
- `app/src/main/res/drawable/logo.jpg`
- `app/src/main/res/drawable/unu_logo.jpg`
- `app/src/main/res/drawable/unu_style_reference.jpg`
- Many vector XML drawables and launcher XML resources under `drawable` and `mipmap-*`.

## Current Database Image References

`destinations.images_json`:

- Stores either arrays of URL strings or richer objects with `url`, `source_page_url`, `source`, `credit`, `license_note`, `order`, `is_primary`, and `match_score`.
- Some values point to local `/images/destinations/...`.
- Some values point to external URLs.
- Some rows are empty `[]`.

`destination_images`:

- Normalized active image rows with `destination_id`, `rag_place_id`, `image_url`, `source`, credit/license fields, `is_primary`, and `status`.
- Node reads this table first and only falls back to `destinations.images_json` if no active image rows exist.

`destination_image_candidates`:

- Staging table for candidate images before approval/promotion.
- Useful for operations and curation, not app runtime.

## Current Image Pipeline Files

Active pipeline files:

- `backend/rag/data/image_pipeline/priority_seed/*.csv`
- `backend/rag/data/image_pipeline/priority_matched/*.csv`
- `backend/rag/data/image_pipeline/valid/*.csv`
- `backend/rag/data/image_pipeline/final/*.csv`
- `backend/rag/data/image_pipeline/reports/*.csv`

Archive pipeline files:

- `backend/rag/_archive/image_pipeline_intermediate/**`
- Includes raw candidates, invalid candidates, retry chunks, backups, and historical promotion outputs.

Scripts found:

- Collect/search/discover image sources.
- Validate URLs.
- Score candidates.
- Promote valid candidates to `destination_images`.
- Rebuild `destinations.images_json` from local webp files.
- Check local image coverage and source mismatches.

## Android Image Usage

Android loads destination images from the API `Destination.images` list using Glide.

Behavior:

- If the URL starts with `http://` or `https://`, Android loads it directly.
- Otherwise Android prepends the backend base URL, turning `/images/...` into a backend-served absolute URL.
- If no image exists, Android shows `R.drawable.placeholder_destination`.

The Android app does not appear to store destination content locally in assets. It relies on backend API responses for app place data and images.

## Image Data Problems

- Image data is duplicated between `destinations.images_json`, `destination_images`, local webp folders, CSV pipeline files, and archive backups.
- `images_json` has mixed formats: simple strings and object arrays.
- Some image folders use `rag_place_id`; some use slug-style names. The stable key strategy is not fully consistent.
- Some SQL image references point to `/images/destinations/...`; others point to external HTTP URLs.
- `destination_images` does not preserve every candidate-level detail, such as source page URL or image order beyond `is_primary`.
- Local files are served from Node, but database rows are the only reliable way to know which files are active for app display.

## V2 Recommendation

Keep images out of the two main tables except for a denormalized primary image URL if the app needs it for fast cards.

Recommended supporting tables:

- `place_images`: approved runtime images.
- `place_image_candidates`: optional staging/review table if image curation continues.

Recommended `place_images` responsibilities:

- Link to `app_places.id` and optionally `rag_knowledge_base.place_id`.
- Store `url`, `storage_type` (`local`, `external`, `upload`), `source`, `source_page_url`, `credit`, `license_note`, `sort_order`, `is_primary`, `status`.
- Treat `/images/...` local URLs and external URLs uniformly at API output time.

Recommended migration rule:

- Prefer `destination_images` active rows over `destinations.images_json`.
- Use `destinations.images_json` only to backfill missing rows or preserve richer provenance.
- Keep local webp files in place during migration and verify each `/images/destinations/...` database URL resolves to an existing file.
