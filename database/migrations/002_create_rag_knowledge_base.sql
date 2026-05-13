-- UNUtrip v2 - Migration 002
-- Purpose: Create the v2 `rag_knowledge_base` table (schema only).
-- Safety:
-- - Creates v2 tables only (no data migration in this file).
-- - Does NOT drop or alter any legacy tables.
-- - Uses CREATE TABLE IF NOT EXISTS for idempotency.
--
-- Locked decisions implemented:
-- - First-cut RAG source is `rag_places` (data migration deferred).
-- - `last_updated` stays VARCHAR-compatible in first migration (do NOT convert to DATETIME yet).
-- - App rating is NOT stored/derived here; `quality_score` is RAG-only.

CREATE TABLE IF NOT EXISTS `rag_knowledge_base` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `knowledge_key` varchar(100) NOT NULL COMMENT 'Deterministic key (first cut: derive from rag_places.place_id); generation happens in data migration',
  `place_key` varchar(50) DEFAULT NULL COMMENT 'Links to app_places.place_key when place-centric',
  `app_place_id` int(11) DEFAULT NULL COMMENT 'Optional link to app_places.id (reused destinations.id)',
  `title` varchar(500) DEFAULT NULL,
  `knowledge_type` varchar(50) NOT NULL COMMENT 'First cut: place (from rag_places); other types deferred',

  `content` longtext DEFAULT NULL,
  `summary` text DEFAULT NULL,

  `province` varchar(255) DEFAULT NULL,
  `city` varchar(255) DEFAULT NULL,
  `area` varchar(255) DEFAULT NULL,
  `destination_group` varchar(255) DEFAULT NULL,
  `address` text DEFAULT NULL,
  `latitude` double DEFAULT NULL,
  `longitude` double DEFAULT NULL,

  `aliases_json` text DEFAULT NULL,
  `category_main` varchar(255) DEFAULT NULL,
  `category_sub` varchar(255) DEFAULT NULL,
  `category_main_norm` varchar(255) DEFAULT NULL,
  `category_sub_norm` varchar(255) DEFAULT NULL,

  `tags_json` text DEFAULT NULL,
  `interest_tags_json` text DEFAULT NULL,
  `suitable_for_json` text DEFAULT NULL,
  `avoid_for_json` text DEFAULT NULL,

  `open_time` varchar(20) DEFAULT NULL,
  `close_time` varchar(20) DEFAULT NULL,
  `best_time_of_day_json` text DEFAULT NULL,
  `suggested_slot` varchar(50) DEFAULT NULL,
  `slot_norm` varchar(50) DEFAULT NULL,
  `duration_minutes` int(11) DEFAULT NULL,
  `is_night_activity` tinyint(1) NOT NULL DEFAULT 0,
  `is_free` tinyint(1) NOT NULL DEFAULT 0,
  `entry_fee_min` double DEFAULT NULL,
  `entry_fee_max` double DEFAULT NULL,
  `budget_level` varchar(50) DEFAULT NULL,
  `budget_level_norm` varchar(50) DEFAULT NULL,
  `price_note` text DEFAULT NULL,
  `walking_level` varchar(50) DEFAULT NULL,
  `walking_level_norm` varchar(50) DEFAULT NULL,
  `activity_level` varchar(50) DEFAULT NULL,
  `activity_level_norm` varchar(50) DEFAULT NULL,
  `elderly_friendly` varchar(20) DEFAULT NULL,
  `elderly_friendly_norm` tinyint(1) NOT NULL DEFAULT 0,
  `kid_friendly` varchar(20) DEFAULT NULL,
  `kid_friendly_norm` tinyint(1) NOT NULL DEFAULT 0,

  `nearby_area_json` text DEFAULT NULL,
  `transport_suggestion_json` text DEFAULT NULL,

  `quality_score` double DEFAULT NULL COMMENT 'RAG/curation only; never app rating',
  `recommended_use` varchar(50) DEFAULT NULL,
  `recommended_use_norm` varchar(50) DEFAULT NULL,
  `is_generic` tinyint(1) NOT NULL DEFAULT 0,
  `must_not_schedule_as_main` tinyint(1) NOT NULL DEFAULT 0,
  `requires_realtime_check` tinyint(1) NOT NULL DEFAULT 0,
  `realtime_fields_json` text DEFAULT NULL,

  `source` text DEFAULT NULL,
  `source_url` text DEFAULT NULL,
  `last_updated` varchar(50) DEFAULT NULL COMMENT 'Locked: keep VARCHAR-compatible text in first cut',

  `is_active` tinyint(1) NOT NULL DEFAULT 1,
  `search_text` longtext DEFAULT NULL,
  `raw_json` longtext DEFAULT NULL,

  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),

  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_rag_knowledge_base_knowledge_key` (`knowledge_key`),
  KEY `idx_rag_kb_place_key` (`place_key`),
  KEY `idx_rag_kb_app_place_id` (`app_place_id`),
  KEY `idx_rag_kb_province` (`province`),
  KEY `idx_rag_kb_city` (`city`),
  KEY `idx_rag_kb_area` (`area`),
  KEY `idx_rag_kb_category_main` (`category_main`),
  KEY `idx_rag_kb_category_sub` (`category_sub`),
  KEY `idx_rag_kb_budget_norm` (`budget_level_norm`),
  KEY `idx_rag_kb_walking_norm` (`walking_level_norm`),
  KEY `idx_rag_kb_recommended_use_norm` (`recommended_use_norm`),
  KEY `idx_rag_kb_knowledge_type` (`knowledge_type`),
  KEY `idx_rag_kb_active` (`is_active`),
  CONSTRAINT `fk_rag_kb_app_place_id` FOREIGN KEY (`app_place_id`) REFERENCES `app_places` (`id`)
    ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

