# Image Migration Plan (Documentation Only)

**Goal:** Define how destination image data moves from the current model to v2 **`place_images`** as the **source of truth** for approved runtime images, with optional **`app_places.primary_image_url`** as denormalized convenience only.

**Authoritative references:** `docs/IMAGE_DATA_AUDIT.md`, `docs/V2_DATABASE_DIRECTION.md`, `docs/CURRENT_DATABASE_AUDIT.md`, `docs/MIGRATION_RISK_REPORT.md`, `docs/DATA_INVENTORY.md`.

**Out of scope for this file:** Migration SQL, backend/Android/RAG code changes, moving or renaming files on disk.

---

## Current state (summary)

| Layer | Role | Notes |
|--------|------|-------|
| `destinations.images_json` | Legacy / fallback blob | Mixed format: string URLs or objects with `url`, provenance, `order`, `is_primary`, etc. |
| `destination_images` | Normalized active rows | Node prefers this over `images_json` when attaching images. |
| `destination_image_candidates` | Staging | Not app runtime. |
| `backend/nodejs/public/images/destinations/` | Local `.webp` files | Served as `/images/destinations/...`; folder naming mixes `rag_place_id` style and slug style. |
| Pipeline CSVs | Ops | `image_pipeline/*` per inventory. |

Android loads from API `Destination.images`; relative `/images/...` paths are resolved against backend base URL (image audit).

---

## Target state (v2)

| Artifact | Role |
|---------|------|
| `place_images` | **Approved runtime images** for `app_places`. |
| `place_image_candidates` | Optional staging (from `destination_image_candidates`). |
| `app_places.primary_image_url` | Optional cache; must stay consistent with `place_images` primary. |

---

## Migration precedence (data)

1. **Primary:** Active rows in `destination_images` (as today: Node reads this first).
2. **Backfill:** `destinations.images_json` only where approved imagery is missing or incomplete in `destination_images`.
3. **Filesystem:** Use disk only for **verification** that `/images/destinations/...` URLs resolve to existing files—not as the authoritative list unless a separate audit decides to insert missing rows ( **open question** ).

This order matches `docs/IMAGE_DATA_AUDIT.md` and risk report mitigations.

---

## Row-level mapping

| Target field | Source | Rule |
|--------------|--------|------|
| `app_place_id` | `destination_images.destination_id` | Map via `place_id_map` to new `app_places.id`. |
| `place_key` | `destination_images.rag_place_id` or `app_places.place_key` | Copy when known. |
| `image_url` | `destination_images.image_url` | Preserve exact string for URL stability. |
| `source`, `credit`, `license_note` | `destination_images` | Direct copy. |
| `is_primary` | `destination_images.is_primary` | Direct copy. |
| `status` | `destination_images.status` | Copy; define “active” filter consistently with current Node behavior (**open question**: exact values). |
| `source_page_url` | `destination_images` if column exists; else parse `images_json` objects | Image audit notes candidates have richer metadata than some DB rows. |
| `sort_order` | `images_json` object `order`; or infer from array order | **Open question** if `destination_images` has no order column. |
| `storage_type` | Derive from `image_url` | Direction suggests `local`, `external`, `upload`: e.g. prefix `/images/` → local; `review` uploads under `/uploads/` are separate domain (not destination gallery). |

**`primary_image_url` on `app_places`:**

- Set from the single approved `place_images` row where `is_primary` and active `status` (definition TBD).
- If multiple primaries or none: **open question** (tie-break: highest `sort_order`, first URL, or ops fix).

---

## Handling `images_json` formats

- **String elements:** Treat as `image_url`; minimal provenance.
- **Object elements:** Extract `url`, `source_page_url`, `source`, `credit`, `license_note`, `order`, `is_primary`, `match_score` when present (field names per image audit).

**Rules:**

- Prefer not to duplicate rows already satisfied by `destination_images`.
- When backfilling, preserve provenance in `place_images` columns where possible.

**Open questions:**

- De-duplication key: URL only vs URL + `app_place_id`.
- Whether low `match_score` objects are imported or quarantined.

---

## Local file verification

Per risk/image audits:

- For each migrated row whose `image_url` points under `/images/destinations/...`, confirm a file exists under `backend/nodejs/public/images/destinations/` at the expected path.
- Record failures for manual fix (broken links risk).

**Open questions:**

- Policy when DB references a missing local file (remove row, flag, or regenerate from CSV pipeline).

---

## Candidate pipeline

- `destination_image_candidates` / CSV pipeline feeds **staging**, not necessarily **`place_images`** until promoted.
- Promotion process today is script-driven (audit); v2 assumes same operational discipline unless redefined.

**Open questions:**

- Formal promotion steps from `place_image_candidates` → `place_images`.
- Whether batch codes map to `data_import_batches` (optional table in direction).

---

## Folder naming vs `place_key`

Audit: folders may be `rag_place_id` style or slug (e.g. `ha-noi__ho-hoan-kiem`).

- **`place_id_map.image_folder_key`** may record the folder string for reconciliation (schema design).
- **Open questions:** Automatic mapping from slug-only folders to DB rows; handling multiple folders per place.

---

## API / Android considerations (contract only)

- V2 should continue to expose a list equivalent to current `Destination.images` unless API versioning changes (direction: keep shape or update app after validation).
- Relative URLs remain valid if backend base URL concatenation behavior is unchanged.

**Open questions:** Whether `primary_image_url` is exposed in list endpoints for performance.

---

## Checklist references

See **`VALIDATION_CHECKLIST.md`** for verification steps (counts, URL health, primary uniqueness).

---

## Open questions (consolidated)

1. Exact `destination_images.status` values and filter for “active”.
2. Whether to preserve `destination_images.id` as `place_images.id`.
3. Max images per `app_place_id` and dedup rules.
4. Default when no primary is marked but multiple images exist.
5. Whether to import from disk scan when DB has no rows but files exist.
6. Conflict resolution between `images_json` and `destination_images` when URLs differ for same slot.
