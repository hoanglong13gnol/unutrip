# Exact Legacy Schema Audit (from `unudata-v2.sql`)

**Phase:** UNUtrip v2 database-first refactor — exact legacy schema audit (pre-migration).  
**Hard rule:** This document is **evidence-only** from `unudata-v2.sql`. No migration SQL is proposed here.

## Scope

Tables audited (legacy):

- `destinations`
- `rag_places`
- `destination_images`
- `favorites`
- `reviews`
- `itinerary_items`

Questions answered (exactly, from dump):

1. Exact columns + SQL types for `destinations`
2. Exact columns + SQL types for `rag_places`
3. Exact columns + SQL types for `destination_images`
4. Exact values used in `destination_images.status`
5. Exact values used in `destinations.category`
6. Exact place reference columns in `favorites`
7. Exact place reference columns in `reviews`
8. Exact place reference columns in `itinerary_items`
9. Existing foreign keys / indexes related to these tables
10. v2 proposed fields that do **not** have a reliable legacy source (cross-ref summary; details live in `SCHEMA_DECISIONS_TO_LOCK.md`)

---

## 1) `destinations` — exact columns and SQL types

Source: `unudata-v2.sql` `CREATE TABLE \`destinations\``.

```sql
CREATE TABLE `destinations` (
  `id` int(11) NOT NULL,
  `rag_place_id` varchar(50) DEFAULT NULL,
  `name` varchar(500) NOT NULL,
  `description` text NOT NULL,
  `short_description` text DEFAULT NULL,
  `address` text DEFAULT NULL,
  `city` varchar(255) DEFAULT NULL,
  `province` varchar(255) DEFAULT NULL,
  `area` varchar(255) DEFAULT NULL,
  `latitude` double DEFAULT NULL,
  `longitude` double DEFAULT NULL,
  `category` varchar(100) NOT NULL DEFAULT 'other',
  `category_main` varchar(255) DEFAULT NULL,
  `category_sub` varchar(255) DEFAULT NULL,
  `images_json` text NOT NULL DEFAULT '[]',
  `image_source` varchar(100) DEFAULT NULL,
  `image_credit` text DEFAULT NULL,
  `rating` double NOT NULL DEFAULT 0,
  `review_count` int(11) NOT NULL DEFAULT 0,
  `open_time` varchar(20) DEFAULT NULL,
  `close_time` varchar(20) DEFAULT NULL,
  `entry_fee` double DEFAULT NULL,
  `budget_level` varchar(50) DEFAULT NULL,
  `walking_level` varchar(50) DEFAULT NULL,
  `kid_friendly` tinyint(1) NOT NULL DEFAULT 0,
  `elderly_friendly` tinyint(1) NOT NULL DEFAULT 0,
  `recommended_use` varchar(50) DEFAULT NULL,
  `tags_json` text NOT NULL DEFAULT '[]',
  `is_active` tinyint(1) NOT NULL DEFAULT 1,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
```

**Auto increment (dump-level constraint):**

- `ALTER TABLE \`destinations\` MODIFY \`id\` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=11185;`

---

## 2) `rag_places` — exact columns and SQL types

Source: `unudata-v2.sql` `CREATE TABLE \`rag_places\``.

```sql
CREATE TABLE `rag_places` (
  `id` int(11) NOT NULL,
  `place_id` varchar(50) NOT NULL,
  `destination_id` int(11) DEFAULT NULL,
  `name` varchar(500) NOT NULL,
  `aliases_json` text DEFAULT NULL,
  `province` varchar(255) DEFAULT NULL,
  `city` varchar(255) DEFAULT NULL,
  `area` varchar(255) DEFAULT NULL,
  `destination_group` varchar(255) DEFAULT NULL,
  `address` text DEFAULT NULL,
  `latitude` double DEFAULT NULL,
  `longitude` double DEFAULT NULL,
  `category_main` varchar(255) DEFAULT NULL,
  `category_sub` varchar(255) DEFAULT NULL,
  `category_main_norm` varchar(255) DEFAULT NULL,
  `category_sub_norm` varchar(255) DEFAULT NULL,
  `tags_json` text DEFAULT NULL,
  `interest_tags_json` text DEFAULT NULL,
  `suitable_for_json` text DEFAULT NULL,
  `avoid_for_json` text DEFAULT NULL,
  `description` text DEFAULT NULL,
  `short_description` text DEFAULT NULL,
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
  `quality_score` double DEFAULT NULL,
  `recommended_use` varchar(50) DEFAULT NULL,
  `recommended_use_norm` varchar(50) DEFAULT NULL,
  `is_generic` tinyint(1) NOT NULL DEFAULT 0,
  `must_not_schedule_as_main` tinyint(1) NOT NULL DEFAULT 0,
  `requires_realtime_check` tinyint(1) NOT NULL DEFAULT 0,
  `realtime_fields_json` text DEFAULT NULL,
  `source` text DEFAULT NULL,
  `source_url` text DEFAULT NULL,
  `last_updated` varchar(50) DEFAULT NULL,
  `is_active` tinyint(1) NOT NULL DEFAULT 1,
  `search_text` longtext DEFAULT NULL,
  `raw_json` longtext DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
```

**Auto increment (dump-level constraint):**

- `ALTER TABLE \`rag_places\` MODIFY \`id\` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=11185;`

---

## 3) `destination_images` — exact columns and SQL types

Source: `unudata-v2.sql` `CREATE TABLE \`destination_images\``.

```sql
CREATE TABLE `destination_images` (
  `id` int(11) NOT NULL,
  `destination_id` int(11) NOT NULL,
  `rag_place_id` varchar(50) DEFAULT NULL,
  `image_url` text NOT NULL,
  `source` varchar(100) DEFAULT NULL,
  `credit` text DEFAULT NULL,
  `license_note` text DEFAULT NULL,
  `is_primary` tinyint(1) NOT NULL DEFAULT 0,
  `status` varchar(50) NOT NULL DEFAULT 'active',
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
```

**Auto increment (dump-level constraint):**

- `ALTER TABLE \`destination_images\` MODIFY \`id\` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=1107;`

---

## 4) `destination_images.status` — exact values used

Extracted from values present in the dump (`INSERT INTO destination_images ... status ...`):

- `active`

Notes:

- The column default is also `DEFAULT 'active'`.

---

## 5) `destinations.category` — exact values used

Extracted from values present in the dump (`INSERT INTO destinations ... category ...`):

- `beach`
- `checkin`
- `city`
- `culture`
- `food`
- `heritage`
- `mountain`
- `nature`
- `religious`

Notes:

- Column definition is `varchar(100) NOT NULL DEFAULT 'other'`.
- The value `other` is the **default**, but it did **not** appear as an inserted value in this dump snapshot.

---

## 6) `favorites` — exact place reference columns

Source: `unudata-v2.sql` `CREATE TABLE \`favorites\``.

```sql
CREATE TABLE `favorites` (
  `user_id` int(11) NOT NULL,
  `destination_id` int(11) NOT NULL,
  `created_at` datetime NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
```

**Place reference column(s):**

- `favorites.destination_id` (int(11) NOT NULL) → references `destinations.id` (FK; see below)

---

## 7) `reviews` — exact place reference columns

Source: `unudata-v2.sql` `CREATE TABLE \`reviews\``.

```sql
CREATE TABLE `reviews` (
  `id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `destination_id` int(11) NOT NULL,
  `rating` double NOT NULL,
  `comment` text NOT NULL,
  `images_json` text DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
```

**Place reference column(s):**

- `reviews.destination_id` (int(11) NOT NULL) → references `destinations.id` (FK; see below)

**Auto increment (dump-level constraint):**

- `ALTER TABLE \`reviews\` MODIFY \`id\` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;`

---

## 8) `itinerary_items` — exact place reference columns

Source: `unudata-v2.sql` `CREATE TABLE \`itinerary_items\``.

```sql
CREATE TABLE `itinerary_items` (
  `id` int(11) NOT NULL,
  `day_id` int(11) NOT NULL,
  `destination_id` int(11) NOT NULL,
  `start_time` varchar(20) NOT NULL,
  `end_time` varchar(20) NOT NULL,
  `note` text DEFAULT NULL,
  `order_index` int(11) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
```

**Place reference column(s):**

- `itinerary_items.destination_id` (int(11) NOT NULL) → references `destinations.id` (FK; see below)

**Auto increment (dump-level constraint):**

- `ALTER TABLE \`itinerary_items\` MODIFY \`id\` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=64;`

---

## 9) Existing indexes and foreign keys (these tables)

### Indexes

From the dump `ALTER TABLE ... ADD KEY` blocks:

- `destinations`
  - `PRIMARY KEY (id)`
  - `UNIQUE KEY uq_destinations_rag_place_id (rag_place_id)`
  - `KEY idx_destinations_province (province)`
  - `KEY idx_destinations_city (city)`
  - `KEY idx_destinations_area (area)`
  - `KEY idx_destinations_category (category)`
  - `KEY idx_destinations_category_main (category_main)`
  - `KEY idx_destinations_active (is_active)`

- `destination_images`
  - `PRIMARY KEY (id)`
  - `KEY idx_destination_images_destination_id (destination_id)`
  - `KEY idx_destination_images_rag_place_id (rag_place_id)`
  - `KEY idx_destination_images_status (status)`

- `favorites`
  - `PRIMARY KEY (user_id, destination_id)` (composite)
  - `KEY idx_favorites_destination_id (destination_id)`

- `itinerary_items`
  - `PRIMARY KEY (id)`
  - `KEY idx_itinerary_items_day_id (day_id)`
  - `KEY idx_itinerary_items_destination_id (destination_id)`

- `rag_places`
  - `PRIMARY KEY (id)`
  - `UNIQUE KEY uq_rag_places_place_id (place_id)`
  - `KEY idx_rag_places_destination_id (destination_id)`
  - `KEY idx_rag_places_province (province)`
  - `KEY idx_rag_places_city (city)`
  - `KEY idx_rag_places_area (area)`
  - `KEY idx_rag_places_category_main (category_main)`
  - `KEY idx_rag_places_category_sub (category_sub)`
  - `KEY idx_rag_places_budget (budget_level_norm)`
  - `KEY idx_rag_places_walking (walking_level_norm)`
  - `KEY idx_rag_places_recommended_use (recommended_use_norm)`
  - `KEY idx_rag_places_active (is_active)`

- `reviews`
  - `PRIMARY KEY (id)`
  - `KEY idx_reviews_destination_id (destination_id)`
  - `KEY idx_reviews_user_id (user_id)`

### Foreign keys

From the dump `ALTER TABLE ... ADD CONSTRAINT ... FOREIGN KEY ...` blocks:

- `destination_images.destination_id` → `destinations.id`
  - `ON DELETE CASCADE ON UPDATE CASCADE`

- `favorites.destination_id` → `destinations.id`
  - `ON DELETE CASCADE ON UPDATE CASCADE`

- `itinerary_items.destination_id` → `destinations.id`
  - `ON DELETE CASCADE ON UPDATE CASCADE`

- `rag_places.destination_id` → `destinations.id`
  - `ON DELETE SET NULL ON UPDATE CASCADE`

- `reviews.destination_id` → `destinations.id`
  - `ON DELETE CASCADE ON UPDATE CASCADE`

---

## 10) Proposed v2 fields without a reliable legacy source (summary pointer)

This audit is **legacy-schema-only**. The cross-reference outcome (which v2-proposed fields do not have a reliable legacy source) is documented in:

- `database/docs/SCHEMA_DECISIONS_TO_LOCK.md`

