-- Nhanh: đưa dữ liệu từ bảng `destinations` (schema kiểu `backend/nodejs/database.sql`)
-- vào `app_places` — đúng bảng mà backend Node (/api/destinations/*) đang đọc.
--
-- Điều kiện:
-- 1. Đã chạy `database/migrations/001_create_app_places.sql` (có bảng `app_places`).
-- 2. Bảng `destinations` đã có dữ liệu (ví dụ sau khi import `backend/nodejs/database.sql`).
--
-- Lưu ý:Dump “v2” đầy đủ của dự án dùng chuỗi migration `006_populate_app_places.sql` thay vì file này.

SET NAMES utf8mb4;

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
  d.`id`,
  CONCAT('MANUAL_', d.`id`) AS `place_key`,
  CAST(d.`name` AS CHAR(500)) COLLATE utf8mb4_general_ci AS `name`,
  COALESCE(NULLIF(TRIM(CAST(d.`description` AS CHAR)), ''), '-') AS `description`,
  NULL AS `short_description`,
  d.`address`,
  d.`city`,
  d.`province`,
  NULL AS `area`,
  d.`latitude`,
  d.`longitude`,
  CASE LOWER(TRIM(d.`category`))
    WHEN 'beach' THEN 'beach'
    WHEN 'checkin' THEN 'checkin'
    WHEN 'city' THEN 'city'
    WHEN 'culture' THEN 'culture'
    WHEN 'food' THEN 'food'
    WHEN 'heritage' THEN 'heritage'
    WHEN 'historical' THEN 'heritage'
    WHEN 'mountain' THEN 'mountain'
    WHEN 'nature' THEN 'nature'
    WHEN 'religious' THEN 'religious'
    WHEN 'theme_park' THEN 'culture'
    WHEN 'attraction' THEN 'checkin'
    WHEN 'other' THEN 'other'
    ELSE 'other'
  END AS `category`,
  d.`open_time`,
  d.`close_time`,
  d.`entry_fee`,
  NULL AS `budget_level`,
  NULL AS `walking_level`,
  0 AS `kid_friendly`,
  0 AS `elderly_friendly`,
  NULL AS `recommended_use`,
  COALESCE(NULLIF(TRIM(d.`tags_json`), ''), '[]') AS `tags_json`,
  NULL AS `primary_image_url`,
  COALESCE(d.`rating`, 0) AS `rating`,
  COALESCE(d.`review_count`, 0) AS `review_count`,
  1 AS `is_active`,
  CURRENT_TIMESTAMP AS `created_at`,
  CURRENT_TIMESTAMP AS `updated_at`
FROM `destinations` d
ON DUPLICATE KEY UPDATE
  `name` = VALUES(`name`),
  `description` = VALUES(`description`),
  `address` = VALUES(`address`),
  `city` = VALUES(`city`),
  `province` = VALUES(`province`),
  `latitude` = VALUES(`latitude`),
  `longitude` = VALUES(`longitude`),
  `category` = VALUES(`category`),
  `open_time` = VALUES(`open_time`),
  `close_time` = VALUES(`close_time`),
  `entry_fee` = VALUES(`entry_fee`),
  `tags_json` = VALUES(`tags_json`),
  `rating` = VALUES(`rating`),
  `review_count` = VALUES(`review_count`),
  `is_active` = VALUES(`is_active`),
  `updated_at` = CURRENT_TIMESTAMP;
