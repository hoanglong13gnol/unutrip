/*
  UnuTrip DB cleanup step 04: clean app-facing taxonomy in destinations.

  Design after cleanup:
    - destinations.category      = canonical app filter code
    - destinations.category_main = canonical app main code, same as category
    - destinations.category_sub  = NULL in app table
    - raw/detailed taxonomy stays in rag_places

  Run after backing up database.
*/

CREATE TABLE IF NOT EXISTS destinations_app_taxonomy_backup_before_step04 AS
SELECT
    id,
    rag_place_id,
    name,
    province,
    category,
    category_main,
    category_sub,
    rating,
    review_count,
    updated_at
FROM destinations;

-- 1) Fix known category mistakes caused by previous broad rules.
-- Urban lakes and city promenade lakes are check-in/landmark spots in the app.
UPDATE destinations
SET category = 'checkin'
WHERE LOWER(name) IN (
    'hồ tây',
    'hồ hoàn kiếm',
    'hồ trúc bạch',
    'hồ bảy mẫu'
);

-- Inland/ecotourism lakes should not be mountain just because they are lakes.
UPDATE destinations
SET category = 'nature'
WHERE category = 'mountain'
  AND (
      LOWER(COALESCE(category_main, '')) LIKE '%lake%'
      OR LOWER(COALESCE(category_sub, '')) LIKE '%lake%'
      OR LOWER(COALESCE(category_main, '')) LIKE '%hồ%'
      OR LOWER(COALESCE(category_sub, '')) LIKE '%hồ%'
  )
  AND LOWER(name) NOT IN (
      'hồ tây',
      'hồ hoàn kiếm',
      'hồ trúc bạch',
      'hồ bảy mẫu'
  );

-- Specific inland false positive from old beach rule.
UPDATE destinations
SET category = 'nature'
WHERE name = 'Đảo Tiên Cát Tiên'
  AND province = 'Đồng Nai';

-- 2) Normalize app-facing taxonomy columns in destinations.
-- Raw detailed taxonomy is preserved in rag_places.
-- destinations must not mix raw Vietnamese/English taxonomy like lake, museum, biển đảo.
UPDATE destinations
SET category_main = category,
    category_sub = NULL
WHERE category IN (
    'beach',
    'mountain',
    'city',
    'heritage',
    'nature',
    'checkin',
    'food',
    'culture',
    'religious'
);

-- 3) Keep app rating based on real reviews only.
-- quality_score belongs to rag_places, not destinations.rating.
UPDATE destinations d
LEFT JOIN (
    SELECT
        destination_id,
        AVG(rating) AS avg_rating,
        COUNT(*) AS cnt
    FROM reviews
    GROUP BY destination_id
) r ON r.destination_id = d.id
SET d.rating = COALESCE(r.avg_rating, 0),
    d.review_count = COALESCE(r.cnt, 0);

-- 4) Audit output.
SELECT
    'CATEGORY_COUNTS' AS section,
    category,
    COUNT(*) AS total
FROM destinations
GROUP BY category
ORDER BY total DESC;

SELECT
    'DESTINATIONS_TAXONOMY_NOT_CLEAN' AS section,
    id,
    name,
    province,
    category,
    category_main,
    category_sub
FROM destinations
WHERE category_main <> category
   OR category_sub IS NOT NULL
LIMIT 100;

SELECT
    'MOUNTAIN_LAKE_REMAINING' AS section,
    id,
    name,
    province,
    category,
    category_main,
    category_sub
FROM destinations
WHERE category = 'mountain'
  AND (
      LOWER(COALESCE(name, '')) LIKE '%hồ%'
      OR LOWER(COALESCE(category_main, '')) LIKE '%lake%'
      OR LOWER(COALESCE(category_sub, '')) LIKE '%lake%'
      OR LOWER(COALESCE(category_main, '')) LIKE '%hồ%'
      OR LOWER(COALESCE(category_sub, '')) LIKE '%hồ%'
  )
LIMIT 100;

SELECT
    'RATING_AUDIT' AS section,
    COUNT(*) AS destinations_with_rating_gt_0
FROM destinations
WHERE rating > 0;