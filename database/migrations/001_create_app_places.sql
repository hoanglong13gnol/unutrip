-- UNUtrip v2 - Migration 001
-- Purpose: Create the v2 `app_places` table (schema only).
-- Safety:
-- - Creates v2 tables only (no data migration in this file).
-- - Does NOT drop or alter any legacy tables.
-- - Uses CREATE TABLE IF NOT EXISTS for idempotency.
--
-- Locked decisions implemented:
-- - `app_places.id` reuses `destinations.id` (no new ids generated in first cut).
-- - `place_key` is stored here but populated later using the locked 3-step rule.
-- - `category` is constrained to the controlled list; `other` is allowed for legacy/default compatibility and must be reviewed if present.

-- `tags_json` dùng VARCHAR + DEFAULT để tránh lỗi 1101 (TEXT/BLOB không DEFAULT trên một số engine/chế độ).
CREATE TABLE IF NOT EXISTS `app_places` (
  `id` int(11) NOT NULL COMMENT 'Reuses legacy destinations.id in first v2 cut',
  `place_key` varchar(50) NOT NULL COMMENT 'Stable cross-system key; populated by later data migration per locked rule',
  `name` varchar(500) NOT NULL,
  `description` text NOT NULL,
  `short_description` text DEFAULT NULL,
  `address` text DEFAULT NULL,
  `city` varchar(255) DEFAULT NULL,
  `province` varchar(255) DEFAULT NULL,
  `area` varchar(255) DEFAULT NULL,
  `latitude` double DEFAULT NULL,
  `longitude` double DEFAULT NULL,
  `category` enum('beach','checkin','city','culture','food','heritage','mountain','nature','religious','other') NOT NULL DEFAULT 'other'
    COMMENT 'Controlled list; `other` allowed only as legacy/default and must be flagged for review if present',
  `open_time` varchar(20) DEFAULT NULL,
  `close_time` varchar(20) DEFAULT NULL,
  `entry_fee` double DEFAULT NULL,
  `budget_level` varchar(50) DEFAULT NULL,
  `walking_level` varchar(50) DEFAULT NULL,
  `kid_friendly` tinyint(1) NOT NULL DEFAULT 0,
  `elderly_friendly` tinyint(1) NOT NULL DEFAULT 0,
  `recommended_use` varchar(50) DEFAULT NULL,
  `tags_json` varchar(4096) NOT NULL DEFAULT '[]',
  `primary_image_url` varchar(2048) DEFAULT NULL COMMENT 'Optional denormalized cache; source of truth is place_images',
  `rating` decimal(3,2) DEFAULT NULL COMMENT 'Must be derived from reviews; never from RAG quality_score',
  `review_count` int(11) DEFAULT NULL COMMENT 'Must be derived from reviews',
  `is_active` tinyint(1) NOT NULL DEFAULT 1,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_app_places_place_key` (`place_key`),
  KEY `idx_app_places_province` (`province`),
  KEY `idx_app_places_city` (`city`),
  KEY `idx_app_places_area` (`area`),
  KEY `idx_app_places_category` (`category`),
  KEY `idx_app_places_active` (`is_active`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

