-- UNUtrip v2 - Migration 004
-- Purpose: Create the v2 `place_id_map` table (schema only).
-- Safety:
-- - Creates v2 tables only (no data migration in this file).
-- - Does NOT drop or alter any legacy tables.
-- - Uses CREATE TABLE IF NOT EXISTS for idempotency.
--
-- Locked decisions implemented:
-- - `place_id_map` is mandatory even though numeric ids are reused.
-- - `place_key` rule and any `MANUAL_*` keys will be recorded (later) in `notes`.
--
-- Mapping cardinality note:
-- - Do NOT assume 1:1 between legacy/RAG keys and an app place.
--   Multiple legacy/RAG identifiers may need to map to the same `new_app_place_id`.

CREATE TABLE IF NOT EXISTS `place_id_map` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,

  `old_destination_id` int(11) DEFAULT NULL COMMENT 'Legacy destinations.id',
  `rag_place_id_legacy` varchar(50) DEFAULT NULL COMMENT 'Legacy destinations.rag_place_id (nullable, but unique when present)',
  `rag_place_id` varchar(50) DEFAULT NULL COMMENT 'Legacy rag_places.place_id (unique, NOT NULL in legacy; nullable here for edge cases)',
  `old_rag_destination_id` int(11) DEFAULT NULL COMMENT 'Legacy rag_places.destination_id',

  `new_app_place_id` int(11) NOT NULL COMMENT 'v2 app_places.id (first cut equals old_destination_id when present); multiple legacy keys may map to the same app place',
  `place_key` varchar(100) NOT NULL COMMENT 'Canonical key used across v2 (see locked place_key rule); sized for RAG_ALIAS_* keys',

  `image_folder_key` varchar(255) DEFAULT NULL COMMENT 'Optional: filesystem folder key hint (legacy inconsistencies)',
  `notes` varchar(500) DEFAULT NULL COMMENT 'Manual review notes (e.g., MANUAL_* keys, collisions, missing sources)',

  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),

  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_place_id_map_place_key` (`place_key`),
  UNIQUE KEY `uq_place_id_map_rag_place_id_legacy` (`rag_place_id_legacy`),
  UNIQUE KEY `uq_place_id_map_rag_place_id` (`rag_place_id`),
  KEY `idx_place_id_map_new_app_place_id` (`new_app_place_id`),
  KEY `idx_place_id_map_old_destination_id` (`old_destination_id`),
  KEY `idx_place_id_map_old_rag_destination_id` (`old_rag_destination_id`),
  CONSTRAINT `fk_place_id_map_new_app_place_id` FOREIGN KEY (`new_app_place_id`) REFERENCES `app_places` (`id`)
    ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

