-- UNUtrip v2 - Migration 006 (data migration)
-- Purpose: Populate `app_places` from legacy `destinations` with derived fields.
-- Safety:
-- - Inserts/updates v2 table only.
-- - Does NOT drop or alter legacy tables.
-- - Designed to be re-runnable via ON DUPLICATE KEY UPDATE.
--
-- Locked decisions implemented:
-- - app_places.id = destinations.id (no new ids generated).
-- - place_key rule:
--   1) destinations.rag_place_id
--   2) rag_places.place_id where rag_places.destination_id = destinations.id
--   3) MANUAL_{destinations.id}
-- - rating/review_count computed from reviews aggregate (NOT destinations.rating).
-- - primary_image_url derived from destination_images where status='active':
--   - if any active has is_primary=1 => smallest destination_images.id among those
--   - else => smallest active destination_images.id
--   - else => NULL (do not parse destinations.images_json in this migration)

INSERT INTO `app_places` (
  `id`,
  `place_key`,
  `name`,
  `description`,
  `short_description`,
  `address`,
  `city`,
  `province`,
  `area`,
  `latitude`,
  `longitude`,
  `category`,
  `open_time`,
  `close_time`,
  `entry_fee`,
  `budget_level`,
  `walking_level`,
  `kid_friendly`,
  `elderly_friendly`,
  `recommended_use`,
  `tags_json`,
  `primary_image_url`,
  `rating`,
  `review_count`,
  `is_active`,
  `created_at`,
  `updated_at`
)
SELECT
  d.`id` AS `id`,
  COALESCE(
    d.`rag_place_id`,
    rp_by_dest.`place_id`,
    CONCAT('MANUAL_', d.`id`)
  ) AS `place_key`,
  d.`name`,
  d.`description`,
  d.`short_description`,
  d.`address`,
  d.`city`,
  d.`province`,
  d.`area`,
  d.`latitude`,
  d.`longitude`,
  CASE
    WHEN d.`category` IN ('beach','checkin','city','culture','food','heritage','mountain','nature','religious','other')
      THEN d.`category`
    ELSE 'other'
  END AS `category`,
  d.`open_time`,
  d.`close_time`,
  d.`entry_fee`,
  d.`budget_level`,
  d.`walking_level`,
  d.`kid_friendly`,
  d.`elderly_friendly`,
  d.`recommended_use`,
  d.`tags_json`,
  di_primary.`image_url` AS `primary_image_url`,
  COALESCE(ragg.`avg_rating`, 0) AS `rating`,
  COALESCE(ragg.`review_count`, 0) AS `review_count`,
  d.`is_active`,
  d.`created_at`,
  d.`updated_at`
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
LEFT JOIN (
  SELECT
    rv.`destination_id`,
    AVG(rv.`rating`) AS `avg_rating`,
    COUNT(*) AS `review_count`
  FROM `reviews` rv
  GROUP BY rv.`destination_id`
) ragg
  ON ragg.`destination_id` = d.`id`
LEFT JOIN (
  SELECT
    di.`destination_id`,
    COALESCE(
      MIN(CASE WHEN di.`is_primary` = 1 THEN di.`id` END),
      MIN(di.`id`)
    ) AS `chosen_id`
  FROM `destination_images` di
  WHERE di.`status` = 'active'
  GROUP BY di.`destination_id`
) di_choice
  ON di_choice.`destination_id` = d.`id`
LEFT JOIN `destination_images` di_primary
  ON di_primary.`id` = di_choice.`chosen_id`
ON DUPLICATE KEY UPDATE
  `place_key` = VALUES(`place_key`),
  `name` = VALUES(`name`),
  `description` = VALUES(`description`),
  `short_description` = VALUES(`short_description`),
  `address` = VALUES(`address`),
  `city` = VALUES(`city`),
  `province` = VALUES(`province`),
  `area` = VALUES(`area`),
  `latitude` = VALUES(`latitude`),
  `longitude` = VALUES(`longitude`),
  `category` = VALUES(`category`),
  `open_time` = VALUES(`open_time`),
  `close_time` = VALUES(`close_time`),
  `entry_fee` = VALUES(`entry_fee`),
  `budget_level` = VALUES(`budget_level`),
  `walking_level` = VALUES(`walking_level`),
  `kid_friendly` = VALUES(`kid_friendly`),
  `elderly_friendly` = VALUES(`elderly_friendly`),
  `recommended_use` = VALUES(`recommended_use`),
  `tags_json` = VALUES(`tags_json`),
  `primary_image_url` = VALUES(`primary_image_url`),
  `rating` = VALUES(`rating`),
  `review_count` = VALUES(`review_count`),
  `is_active` = VALUES(`is_active`),
  `created_at` = VALUES(`created_at`),
  `updated_at` = VALUES(`updated_at`);

