-- UNUtrip v2 - Migration 010 (validation queries)
-- Purpose: Read-only SELECT checks for v2 parity and rule compliance.
-- Safety:
-- - SELECT-only; no writes.
-- - Does NOT drop or alter any tables.

-- Counts: legacy vs v2
SELECT 'destinations' AS table_name, COUNT(*) AS row_count FROM destinations;
SELECT 'rag_places' AS table_name, COUNT(*) AS row_count FROM rag_places;
SELECT 'destination_images_active' AS table_name, COUNT(*) AS row_count FROM destination_images WHERE status = 'active';

SELECT 'app_places' AS table_name, COUNT(*) AS row_count FROM app_places;
SELECT 'rag_knowledge_base' AS table_name, COUNT(*) AS row_count FROM rag_knowledge_base;
SELECT 'place_images' AS table_name, COUNT(*) AS row_count FROM place_images;
SELECT 'place_id_map' AS table_name, COUNT(*) AS row_count FROM place_id_map;

-- app_places count vs destinations count
SELECT
  (SELECT COUNT(*) FROM destinations) AS destinations_count,
  (SELECT COUNT(*) FROM app_places) AS app_places_count,
  ((SELECT COUNT(*) FROM destinations) - (SELECT COUNT(*) FROM app_places)) AS diff;

-- rag_knowledge_base count vs rag_places count
SELECT
  (SELECT COUNT(*) FROM rag_places) AS rag_places_count,
  (SELECT COUNT(*) FROM rag_knowledge_base) AS rag_knowledge_base_count,
  ((SELECT COUNT(*) FROM rag_places) - (SELECT COUNT(*) FROM rag_knowledge_base)) AS diff;

-- place_images count vs active destination_images count
SELECT
  (SELECT COUNT(*) FROM destination_images WHERE status = 'active') AS destination_images_active_count,
  (SELECT COUNT(*) FROM place_images) AS place_images_count,
  ((SELECT COUNT(*) FROM destination_images WHERE status = 'active') - (SELECT COUNT(*) FROM place_images)) AS diff;

-- place_id_map rows per app_place_id (should be >= 1 per app_place_id after migration)
SELECT
  new_app_place_id,
  COUNT(*) AS map_rows
FROM place_id_map
GROUP BY new_app_place_id
ORDER BY map_rows DESC, new_app_place_id ASC
LIMIT 50;

-- app_places rows with null/empty place_key
SELECT COUNT(*) AS app_places_null_place_key
FROM app_places
WHERE place_key IS NULL OR place_key = '';

-- app_places rows with null rating or null review_count (expected 0 after COALESCE migration)
SELECT COUNT(*) AS app_places_null_rating_or_review_count
FROM app_places
WHERE rating IS NULL OR review_count IS NULL;

-- duplicate place_key in app_places (should be 0 due to unique constraint; query still useful)
SELECT
  place_key,
  COUNT(*) AS cnt
FROM app_places
GROUP BY place_key
HAVING COUNT(*) > 1
ORDER BY cnt DESC, place_key ASC;

-- place_images with missing app_place_id reference (orphan check)
SELECT COUNT(*) AS place_images_missing_app_place
FROM place_images pi
LEFT JOIN app_places ap ON ap.id = pi.app_place_id
WHERE ap.id IS NULL;

-- rag_knowledge_base rows with missing app_place_id where source rag_places.destination_id was not null
SELECT COUNT(*) AS rag_kb_missing_app_place_id
FROM rag_knowledge_base kb
JOIN rag_places rp
  ON kb.knowledge_key = CONCAT('rag_place:', rp.place_id)
WHERE rp.destination_id IS NOT NULL
  AND (kb.app_place_id IS NULL OR kb.app_place_id <> rp.destination_id);

-- app_places.rating comparison with reviews aggregate (spot mismatches)
SELECT
  ap.id AS destination_id,
  ap.rating AS app_places_rating,
  ap.review_count AS app_places_review_count,
  ragg.avg_rating AS reviews_avg_rating,
  ragg.review_count AS reviews_review_count
FROM app_places ap
LEFT JOIN (
  SELECT
    destination_id,
    AVG(rating) AS avg_rating,
    COUNT(*) AS review_count
  FROM reviews
  GROUP BY destination_id
) ragg
  ON ragg.destination_id = ap.id
WHERE
  (COALESCE(ap.review_count, 0) <> COALESCE(ragg.review_count, 0))
  OR (
    (ap.rating IS NULL AND ragg.avg_rating IS NOT NULL)
    OR (ap.rating IS NOT NULL AND ragg.avg_rating IS NULL)
    OR (ap.rating IS NOT NULL AND ragg.avg_rating IS NOT NULL AND ABS(ap.rating - ragg.avg_rating) > 0.01)
  )
ORDER BY ap.id ASC
LIMIT 200;

-- categories outside controlled list (should be 0; 'other' must be reviewed if present)
SELECT
  category,
  COUNT(*) AS cnt
FROM app_places
GROUP BY category
HAVING category NOT IN ('beach','checkin','city','culture','food','heritage','mountain','nature','religious','other')
ORDER BY cnt DESC, category ASC;

-- primary_image_url null count
SELECT COUNT(*) AS app_places_primary_image_url_null
FROM app_places
WHERE primary_image_url IS NULL OR primary_image_url = '';

-- multiple primary images per app_place_id (should be 0 ideally)
SELECT
  app_place_id,
  COUNT(*) AS primary_count
FROM place_images
WHERE is_primary = 1 AND status = 'active'
GROUP BY app_place_id
HAVING COUNT(*) > 1
ORDER BY primary_count DESC, app_place_id ASC
LIMIT 200;

-- RAG place_id coverage: rag_places rows (destination_id not null) without matching place_id_map.rag_place_id
SELECT
  rp.id AS rag_places_id,
  rp.destination_id,
  rp.place_id
FROM rag_places rp
LEFT JOIN place_id_map pim
  ON pim.rag_place_id = rp.place_id
WHERE rp.destination_id IS NOT NULL
  AND pim.id IS NULL
ORDER BY rp.destination_id ASC, rp.place_id ASC;

-- Count of rag_places rows with destination_id not null
SELECT COUNT(*) AS rag_places_with_destination_id_count
FROM rag_places
WHERE destination_id IS NOT NULL;

-- Count of distinct non-null place_id_map.rag_place_id
SELECT COUNT(DISTINCT rag_place_id) AS place_id_map_distinct_rag_place_id_count
FROM place_id_map
WHERE rag_place_id IS NOT NULL;

-- Groups where one destination_id has more than one rag_places row
SELECT
  rp.destination_id,
  COUNT(*) AS rag_rows
FROM rag_places rp
WHERE rp.destination_id IS NOT NULL
GROUP BY rp.destination_id
HAVING COUNT(*) > 1
ORDER BY rag_rows DESC, rp.destination_id ASC;

-- place_id_map rows per new_app_place_id distribution
SELECT
  x.map_rows_per_app_place,
  COUNT(*) AS app_place_count
FROM (
  SELECT
    new_app_place_id,
    COUNT(*) AS map_rows_per_app_place
  FROM place_id_map
  GROUP BY new_app_place_id
) x
GROUP BY x.map_rows_per_app_place
ORDER BY x.map_rows_per_app_place ASC;

