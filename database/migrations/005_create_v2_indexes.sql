-- UNUtrip v2 - Migration 005
-- Purpose: Add v2 indexes (safe, non-destructive).
-- Safety:
-- - Adds indexes only on v2 tables created in migrations 001-004.
-- - Does NOT drop or alter legacy tables.
-- - Avoids DROP INDEX.
-- - Uses information_schema guards to create indexes only if missing.
--
-- Note on compatibility:
-- - MySQL (8.x) does NOT support `CREATE INDEX IF NOT EXISTS`.
-- - MariaDB supports it in newer versions, but to stay broadly MySQL/MariaDB compatible,
--   this migration uses information_schema + dynamic SQL guards.

-- `app_places` lookup / filtering
SET @db := DATABASE();

-- Helper pattern (repeated): if index missing, create it.

-- app_places(place_key) is unique already in table DDL; no extra index needed.

-- app_places(latitude, longitude) for map/nearby coarse filtering (not spatial index)
SET @idx := 'idx_app_places_lat_lng';
SET @sql := (
  SELECT IF(
    EXISTS(
      SELECT 1
      FROM information_schema.statistics
      WHERE table_schema = @db AND table_name = 'app_places' AND index_name = @idx
    ),
    'SELECT 1',
    'CREATE INDEX idx_app_places_lat_lng ON app_places (latitude, longitude)'
  )
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- place_images(app_place_id, status) for runtime fetches
SET @idx := 'idx_place_images_place_status';
SET @sql := (
  SELECT IF(
    EXISTS(
      SELECT 1
      FROM information_schema.statistics
      WHERE table_schema = @db AND table_name = 'place_images' AND index_name = @idx
    ),
    'SELECT 1',
    'CREATE INDEX idx_place_images_place_status ON place_images (app_place_id, status)'
  )
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- place_images(app_place_id, is_primary) for primary image selection
SET @idx := 'idx_place_images_place_primary';
SET @sql := (
  SELECT IF(
    EXISTS(
      SELECT 1
      FROM information_schema.statistics
      WHERE table_schema = @db AND table_name = 'place_images' AND index_name = @idx
    ),
    'SELECT 1',
    'CREATE INDEX idx_place_images_place_primary ON place_images (app_place_id, is_primary)'
  )
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- rag_knowledge_base(place_key, knowledge_type) for retrieval by place/type
SET @idx := 'idx_rag_kb_place_type';
SET @sql := (
  SELECT IF(
    EXISTS(
      SELECT 1
      FROM information_schema.statistics
      WHERE table_schema = @db AND table_name = 'rag_knowledge_base' AND index_name = @idx
    ),
    'SELECT 1',
    'CREATE INDEX idx_rag_kb_place_type ON rag_knowledge_base (place_key, knowledge_type)'
  )
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- rag_knowledge_base(app_place_id, is_active) for app-linked active docs
SET @idx := 'idx_rag_kb_app_place_active';
SET @sql := (
  SELECT IF(
    EXISTS(
      SELECT 1
      FROM information_schema.statistics
      WHERE table_schema = @db AND table_name = 'rag_knowledge_base' AND index_name = @idx
    ),
    'SELECT 1',
    'CREATE INDEX idx_rag_kb_app_place_active ON rag_knowledge_base (app_place_id, is_active)'
  )
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- place_id_map(old_destination_id, place_key) for validation and legacy tracing
SET @idx := 'idx_place_id_map_old_dest_place_key';
SET @sql := (
  SELECT IF(
    EXISTS(
      SELECT 1
      FROM information_schema.statistics
      WHERE table_schema = @db AND table_name = 'place_id_map' AND index_name = @idx
    ),
    'SELECT 1',
    'CREATE INDEX idx_place_id_map_old_dest_place_key ON place_id_map (old_destination_id, place_key)'
  )
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

