-- UNUtrip v2 - Migration 008 (data migration)
-- Purpose: Populate `place_images` from legacy `destination_images`.
-- Safety:
-- - Inserts v2 rows only.
-- - Does NOT drop or alter legacy tables.
-- - Idempotent via NOT EXISTS check (no unique constraint available on place_images for INSERT IGNORE).
--
-- Locked decisions implemented:
-- - Only destination_images.status = 'active' migrates to runtime place_images.
-- - Do not parse destinations.images_json in this first migration.
-- - Optional fields (source_page_url, sort_order, storage_type) may be NULL.

INSERT INTO `place_images` (
  `app_place_id`,
  `place_key`,
  `image_url`,
  `storage_type`,
  `source`,
  `source_page_url`,
  `credit`,
  `license_note`,
  `sort_order`,
  `is_primary`,
  `status`,
  `created_at`,
  `updated_at`
)
SELECT
  di.`destination_id` AS `app_place_id`,
  COALESCE(ap.`place_key`, di.`rag_place_id`) AS `place_key`,
  di.`image_url`,
  CASE
    WHEN di.`image_url` LIKE '/images/%' THEN 'local'
    WHEN di.`image_url` LIKE 'http://%' OR di.`image_url` LIKE 'https://%' THEN 'external'
    ELSE NULL
  END AS `storage_type`,
  di.`source`,
  NULL AS `source_page_url`,
  di.`credit`,
  di.`license_note`,
  NULL AS `sort_order`,
  di.`is_primary`,
  di.`status`,
  di.`created_at`,
  di.`updated_at`
FROM `destination_images` di
LEFT JOIN `app_places` ap
  ON ap.`id` = di.`destination_id`
WHERE di.`status` = 'active'
  AND NOT EXISTS (
    SELECT 1
    FROM `place_images` pi
    WHERE pi.`app_place_id` = di.`destination_id`
      AND pi.`image_url` = di.`image_url`
  );

