-- UNUtrip v2 - Migration 003
-- Purpose: Create the v2 runtime `place_images` table (schema only).
-- Safety:
-- - Creates v2 tables only (no data migration in this file).
-- - Does NOT drop or alter any legacy tables.
-- - Uses CREATE TABLE IF NOT EXISTS for idempotency.
--
-- Locked decisions referenced:
-- - Only legacy `destination_images.status = active` is eligible to migrate into this runtime table (implemented in a later, separate data migration).

CREATE TABLE IF NOT EXISTS `place_images` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `app_place_id` int(11) NOT NULL COMMENT 'References app_places.id (reused destinations.id)',
  `place_key` varchar(50) DEFAULT NULL COMMENT 'Optional; may match app_places.place_key',

  `image_url` text NOT NULL,
  `storage_type` varchar(20) DEFAULT NULL COMMENT 'Optional (e.g., local/external/upload); nullable in first cut',
  `source` varchar(100) DEFAULT NULL,
  `source_page_url` text DEFAULT NULL COMMENT 'Optional; may be backfilled later',
  `credit` text DEFAULT NULL,
  `license_note` text DEFAULT NULL,

  `sort_order` int(11) DEFAULT NULL COMMENT 'Optional ordering; nullable in first cut',
  `is_primary` tinyint(1) NOT NULL DEFAULT 0,
  `status` varchar(50) NOT NULL DEFAULT 'active' COMMENT 'Runtime status; first cut migrates only legacy status=active',

  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),

  PRIMARY KEY (`id`),
  KEY `idx_place_images_app_place_id` (`app_place_id`),
  KEY `idx_place_images_place_key` (`place_key`),
  KEY `idx_place_images_status` (`status`),
  KEY `idx_place_images_is_primary` (`is_primary`),
  CONSTRAINT `fk_place_images_app_place_id` FOREIGN KEY (`app_place_id`) REFERENCES `app_places` (`id`)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

