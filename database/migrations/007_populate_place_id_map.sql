-- UNUtrip v2 - Migration 007 (data migration)
-- Purpose: Populate `place_id_map` from legacy `destinations` + `rag_places`.
-- Safety:
-- - Inserts/updates v2 table only.
-- - Does NOT drop or alter legacy tables.
-- - Designed to be re-runnable via ON DUPLICATE KEY UPDATE.
--
-- Requirements implemented:
-- - Supports multiple legacy/RAG keys mapping to the same `new_app_place_id`:
--   `new_app_place_id` is indexed but NOT unique (see migration 004).
-- - Uses locked place_key rule and records MANUAL_* in notes.
-- - Leaves image_folder_key NULL (not reliably known in DB-only migration).
-- - Multiple rows per `new_app_place_id` are allowed by design.

-- PART 1: Canonical mapping rows for app place identity.
-- One canonical row per destination id using locked place_key rule.
-- MIN(rag_places.place_id) is used only to choose canonical fallback when
-- destinations.rag_place_id is null.

INSERT INTO `place_id_map` (
  `old_destination_id`,
  `rag_place_id_legacy`,
  `rag_place_id`,
  `old_rag_destination_id`,
  `new_app_place_id`,
  `place_key`,
  `image_folder_key`,
  `notes`,
  `created_at`
)
SELECT
  d.`id` AS `old_destination_id`,
  d.`rag_place_id` AS `rag_place_id_legacy`,
  rp_by_dest.`place_id` AS `rag_place_id`,
  rp_by_dest.`destination_id` AS `old_rag_destination_id`,
  d.`id` AS `new_app_place_id`,
  COALESCE(
    d.`rag_place_id`,
    rp_by_dest.`place_id`,
    CONCAT('MANUAL_', d.`id`)
  ) AS `place_key`,
  NULL AS `image_folder_key`,
  CASE
    WHEN d.`rag_place_id` IS NULL AND rp_by_dest.`place_id` IS NULL
      THEN CONCAT('MANUAL place_key generated: MANUAL_', d.`id`)
    ELSE NULL
  END AS `notes`,
  CURRENT_TIMESTAMP() AS `created_at`
FROM `destinations` d
LEFT JOIN (
  SELECT
    rp.`destination_id`,
    MIN(rp.`place_id`) AS `place_id`
  FROM `rag_places` rp
  WHERE rp.`destination_id` IS NOT NULL
  GROUP BY rp.`destination_id`
) rp_by_dest
  ON rp_by_dest.`destination_id` = d.`id`
ON DUPLICATE KEY UPDATE
  `old_destination_id` = VALUES(`old_destination_id`),
  `rag_place_id_legacy` = VALUES(`rag_place_id_legacy`),
  `rag_place_id` = VALUES(`rag_place_id`),
  `old_rag_destination_id` = VALUES(`old_rag_destination_id`),
  `new_app_place_id` = VALUES(`new_app_place_id`),
  `image_folder_key` = VALUES(`image_folder_key`),
  `notes` = COALESCE(VALUES(`notes`), `notes`);

-- PART 2: Additional alias rows to preserve alternate RAG rawPlaceId resolution.
-- Insert one row per extra rag_places.place_id for the same destination/app place
-- when it is not the canonical place_key for that destination.
-- We use prefixed place_key (RAG_ALIAS_*) to keep place_id_map.place_key globally unique.
-- place_id_map.place_key must be long enough for RAG_ALIAS_{place_id} values.
INSERT INTO `place_id_map` (
  `old_destination_id`,
  `rag_place_id_legacy`,
  `rag_place_id`,
  `old_rag_destination_id`,
  `new_app_place_id`,
  `place_key`,
  `image_folder_key`,
  `notes`,
  `created_at`
)
SELECT
  NULL AS `old_destination_id`,
  NULL AS `rag_place_id_legacy`,
  rp.`place_id` AS `rag_place_id`,
  rp.`destination_id` AS `old_rag_destination_id`,
  d.`id` AS `new_app_place_id`,
  CONCAT('RAG_ALIAS_', rp.`place_id`) AS `place_key`,
  NULL AS `image_folder_key`,
  'Additional rag_places.place_id mapping for same app place' AS `notes`,
  CURRENT_TIMESTAMP() AS `created_at`
FROM `rag_places` rp
JOIN `destinations` d
  ON d.`id` = rp.`destination_id`
LEFT JOIN `app_places` ap
  ON ap.`id` = d.`id`
LEFT JOIN (
  SELECT
    d2.`id` AS `destination_id`,
    COALESCE(
      d2.`rag_place_id`,
      rp2.`place_id`,
      CONCAT('MANUAL_', d2.`id`)
    ) AS `canonical_place_key`
  FROM `destinations` d2
  LEFT JOIN (
    SELECT
      rpx.`destination_id`,
      MIN(rpx.`place_id`) AS `place_id`
    FROM `rag_places` rpx
    WHERE rpx.`destination_id` IS NOT NULL
    GROUP BY rpx.`destination_id`
  ) rp2
    ON rp2.`destination_id` = d2.`id`
) canon
  ON canon.`destination_id` = d.`id`
WHERE rp.`destination_id` IS NOT NULL
  AND rp.`place_id` <> canon.`canonical_place_key`
ON DUPLICATE KEY UPDATE
  `old_rag_destination_id` = VALUES(`old_rag_destination_id`),
  `new_app_place_id` = VALUES(`new_app_place_id`),
  `image_folder_key` = VALUES(`image_folder_key`),
  `notes` = VALUES(`notes`);

