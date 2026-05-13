# UNUtrip Data Inventory

Scope: repository scan for v2 database planning only. No code, data, or images were modified.

## Summary

- SQL files: 3 project files.
- Excel files: 2 project files.
- CSV files: 117 project files after excluding dependency/build folders.
- JSON files: 74 project files after excluding dependency/build folders.
- JSONL files: 6 project files after excluding dependency/build folders.
- Image files: 448 backend destination webp files, plus Android raster assets.
- Main data sources are split across root SQL/Excel, `backend/nodejs`, `backend/rag/data`, `backend/rag/_archive`, Android resources, and backend public images.

## SQL Files

- `unudata-v2.sql`: current large phpMyAdmin/MariaDB dump for database `unudata`. Contains the richest v2-like schema and data.
- `backend/nodejs/database.sql`: older SmartTravel import schema with seed destination rows. It does not include newer RAG/image tables.
- `backend/rag/scripts/04_clean_destinations_app_taxonomy.sql`: cleanup/audit script for app-facing taxonomy in `destinations`.

## Excel Files

- `dataset_vip_fixed.xlsx`: root dataset file.
- `backend/rag/data/raw/dataset_vip_fixed.xlsx`: RAG raw dataset path expected by `backend/rag/core/config.py`.

Note: the FastAPI RAG settings point to `backend/rag/data/raw/dataset_vip_fixed.xlsx` as the configured source workbook and sheet `places_core_dedup_by_id`.

## Current Data Files

Important active project files:

- `backend/nodejs/src/data/destinations.json`: Node-side JSON data file, likely legacy/static seed data.
- `backend/rag/data/processed/places_app.json`: app-oriented processed place export.
- `backend/rag/data/processed/places_app_autofixed.json`: autofixed app-oriented place export.
- `backend/rag/data/processed/places_app_reviewed.json`: reviewed app-oriented source used by import scripts and runtime fallback.
- `backend/rag/data/processed/places_itinerary.json`: itinerary-oriented processed data.
- `backend/rag/data/processed/places_rag_documents.jsonl`: RAG retrieval document corpus.
- `backend/rag/data/processed/category_import_preview.csv`: import preview/audit output.
- `backend/rag/data/cache/gemini_response_cache.jsonl`: LLM response cache.
- `backend/rag/reports/ai_request_logs.jsonl`: active AI request logs.

Important image-pipeline CSV groups:

- `backend/rag/data/image_pipeline/priority_seed/*.csv`: priority seed lists.
- `backend/rag/data/image_pipeline/priority_matched/*.csv`: seed-to-database match outputs.
- `backend/rag/data/image_pipeline/valid/*.csv`: validated image candidate outputs.
- `backend/rag/data/image_pipeline/final/*.csv`: image rows ready for promotion.
- `backend/rag/data/image_pipeline/reports/*.csv`: image coverage and import reports.
- `backend/rag/data/image_prompt_places.csv` and `backend/rag/data/image_updates.csv`: image prompt/update helper files.

Archive data:

- `backend/rag/_archive/data_backups/**`: data and database backups.
- `backend/rag/_archive/image_pipeline_intermediate/**`: raw, invalid, backup, chunk, and retry CSVs from the image pipeline.
- `backend/rag/_archive/rag_reports/reports/**`: historical RAG/admin/test JSON and CSV reports.

## Image Folders

Primary backend image folder:

- `backend/nodejs/public/images/destinations/`
- Contains 161 destination subfolders and 448 `.webp` files.
- Folder names are mostly `rag_place_id` style, for example `AG_0047`, `BDI_0001`, `HCM_0001`, plus slug-style Hanoi folders such as `ha-noi__ho-hoan-kiem`.
- Served by Node as `/images/destinations/<folder>/<file>.webp`.

Android raster/resource image locations:

- `app/src/main/res/drawable/bg_auth_hero.png`
- `app/src/main/res/drawable/ic_edit.png`
- `app/src/main/res/drawable/logo.jpg`
- `app/src/main/res/drawable/unu_logo.jpg`
- `app/src/main/res/drawable/unu_style_reference.jpg`
- `app/src/main/res/drawable/*.xml` and `app/src/main/res/mipmap-*/*.xml` also contain UI vector/launcher resources.

Upload/static folders referenced by code:

- `backend/nodejs/uploads/reviews/`: review images uploaded at runtime.
- `backend/nodejs/uploads/avatars/`: user avatars uploaded at runtime.
- `backend/nodejs/public/images/`: static image root served as `/images`.

## Source-Of-Truth Candidates

- Best current structured place source: `unudata-v2.sql` table `destinations`, with a link to `rag_places` through `rag_place_id`.
- Best current RAG source: `unudata-v2.sql` table `rag_places`, plus `backend/rag/data/processed/places_rag_documents.jsonl`.
- Best reviewed file source before DB import: `backend/rag/data/processed/places_app_reviewed.json`.
- Best image source: `destination_images` table plus `backend/nodejs/public/images/destinations`.

## Duplication Hotspots

- `destinations` exists in both `backend/nodejs/database.sql` and `unudata-v2.sql`, with different schema depth and data volume.
- Place content appears in Excel, processed JSON, SQL dump, RAG documents, and backend static JSON.
- Image URLs appear in `destinations.images_json`, `destination_images`, image candidate CSVs, local webp folders, and archived backups.
- Taxonomy exists as app codes in `destinations.category`, detailed RAG taxonomy in `rag_places.category_main/category_sub`, and category cleanup scripts.
- Ratings are mixed between app display values, review aggregates, and RAG quality scores in cleanup/score scripts.
