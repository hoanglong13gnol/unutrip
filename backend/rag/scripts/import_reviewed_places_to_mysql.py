import json
import pymysql
from pathlib import Path


MYSQL_HOST = "127.0.0.1"
MYSQL_PORT = 3306
MYSQL_USER = "root"
MYSQL_PASSWORD = ""
MYSQL_DB = "unudata"

ROOT_DIR = Path(__file__).resolve().parents[1]
INPUT_FILE = ROOT_DIR / "data" / "processed" / "places_app_reviewed.json"


def safe_str(value, default=""):
    if value is None:
        return default
    return str(value).strip()


def safe_float(value, default=0.0):
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def normalize_category(place):
    main = safe_str(place.get("category_main")).lower()
    sub = safe_str(place.get("category_sub")).lower()
    sub_norm = safe_str(place.get("category_sub_norm")).lower()
    tags = safe_str(place.get("tags_json")).lower()
    interests = safe_str(place.get("interest_tags_json")).lower()
    text = " ".join([main, sub, sub_norm, tags, interests])

    if "biển" in text or "dao" in sub_norm or "bien" in sub_norm:
        return "beach"

    if "núi" in text or "rừng" in text or "sinh thái" in text or "thác" in text:
        return "nature"

    if "di tích" in text or "lịch sử" in text or "văn hóa" in text or "đền" in text or "chùa" in text:
        return "heritage"

    if "ẩm thực" in text or "food" in text or "chợ" in text:
        return "food"

    if "thành phố" in text or "city" in text or "phố" in text:
        return "city"

    return "nature"


def build_tags_json(place):
    tags = []

    for field in [
        "tags_json",
        "interest_tags_json",
        "suitable_for_json",
        "nearby_area_json",
    ]:
        raw = place.get(field)
        if not raw:
            continue

        try:
            parsed = json.loads(raw) if isinstance(raw, str) else raw
            if isinstance(parsed, list):
                tags.extend([safe_str(x) for x in parsed if safe_str(x)])
        except Exception:
            pass

    # add useful normalized fields
    for field in [
        "budget_level_norm",
        "walking_level_norm",
        "activity_level_norm",
        "recommended_use_norm",
    ]:
        val = safe_str(place.get(field))
        if val:
            tags.append(val)

    # deduplicate while preserving order
    seen = set()
    cleaned = []
    for t in tags:
        key = t.lower()
        if key not in seen:
            seen.add(key)
            cleaned.append(t)

    return json.dumps(cleaned, ensure_ascii=False)


def build_images_json(place):
    # RAG dataset currently may not have image URLs.
    # Keep empty list so Android image parser remains safe.
    return json.dumps([], ensure_ascii=False)


def build_description(place):
    desc = safe_str(place.get("description"))
    short = safe_str(place.get("short_description"))

    if desc:
        return desc
    if short:
        return short

    name = safe_str(place.get("name"), "Địa điểm")
    province = safe_str(place.get("province"))
    category_sub = safe_str(place.get("category_sub"))
    return f"{name} là địa điểm du lịch thuộc {province}, phù hợp cho nhu cầu tham quan {category_sub}."


def connect():
    return pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DB,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )


def ensure_columns(conn):
    with conn.cursor() as cur:
        cur.execute("SHOW COLUMNS FROM destinations LIKE 'rag_place_id'")
        exists = cur.fetchone()

        if not exists:
            cur.execute("ALTER TABLE destinations ADD COLUMN rag_place_id VARCHAR(50) NULL AFTER id")

        cur.execute("SHOW INDEX FROM destinations WHERE Key_name = 'idx_destinations_rag_place_id'")
        idx = cur.fetchone()

        if not idx:
            cur.execute("CREATE INDEX idx_destinations_rag_place_id ON destinations (rag_place_id)")

    conn.commit()


def import_places():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Input file not found: {INPUT_FILE}")

    with INPUT_FILE.open("r", encoding="utf-8") as f:
        places = json.load(f)

    print(f"[INFO] Loaded {len(places)} places from {INPUT_FILE}")

    conn = connect()
    inserted = 0
    updated = 0
    skipped = 0

    try:
        ensure_columns(conn)

        with conn.cursor() as cur:
            for place in places:
                if not place.get("is_active", True):
                    skipped += 1
                    continue

                rag_place_id = safe_str(place.get("place_id"))
                name = safe_str(place.get("name"))

                if not rag_place_id or not name:
                    skipped += 1
                    continue

                description = build_description(place)
                address = safe_str(place.get("address")) or safe_str(place.get("area")) or safe_str(place.get("province"))
                city = safe_str(place.get("city")) or safe_str(place.get("province"))
                province = safe_str(place.get("province"))
                latitude = safe_float(place.get("latitude"), 0.0)
                longitude = safe_float(place.get("longitude"), 0.0)
                category = normalize_category(place)
                images_json = build_images_json(place)
                rating = safe_float(place.get("quality_score"), 0.0)
                review_count = 0
                open_time = safe_str(place.get("open_time")) or None
                close_time = safe_str(place.get("close_time")) or None
                entry_fee = safe_float(place.get("entry_fee_min"), 0.0)
                tags_json = build_tags_json(place)

                cur.execute(
                    "SELECT id FROM destinations WHERE rag_place_id = %s LIMIT 1",
                    (rag_place_id,),
                )
                existing = cur.fetchone()

                if existing:
                    cur.execute(
                        """
                        UPDATE destinations
                        SET
                            name = %s,
                            description = %s,
                            address = %s,
                            city = %s,
                            province = %s,
                            latitude = %s,
                            longitude = %s,
                            category = %s,
                            images_json = %s,
                            rating = %s,
                            review_count = %s,
                            open_time = %s,
                            close_time = %s,
                            entry_fee = %s,
                            tags_json = %s
                        WHERE rag_place_id = %s
                        """,
                        (
                            name,
                            description,
                            address,
                            city,
                            province,
                            latitude,
                            longitude,
                            category,
                            images_json,
                            rating,
                            review_count,
                            open_time,
                            close_time,
                            entry_fee,
                            tags_json,
                            rag_place_id,
                        ),
                    )
                    updated += 1
                else:
                    # If old demo row exists with same name/province but no rag_place_id,
                    # update it instead of inserting duplicate.
                    cur.execute(
                        """
                        SELECT id FROM destinations
                        WHERE rag_place_id IS NULL
                          AND name = %s
                          AND province = %s
                        LIMIT 1
                        """,
                        (name, province),
                    )
                    same_name = cur.fetchone()

                    if same_name:
                        cur.execute(
                            """
                            UPDATE destinations
                            SET
                                rag_place_id = %s,
                                description = %s,
                                address = %s,
                                city = %s,
                                latitude = %s,
                                longitude = %s,
                                category = %s,
                                images_json = %s,
                                rating = %s,
                                review_count = %s,
                                open_time = %s,
                                close_time = %s,
                                entry_fee = %s,
                                tags_json = %s
                            WHERE id = %s
                            """,
                            (
                                rag_place_id,
                                description,
                                address,
                                city,
                                latitude,
                                longitude,
                                category,
                                images_json,
                                rating,
                                review_count,
                                open_time,
                                close_time,
                                entry_fee,
                                tags_json,
                                same_name["id"],
                            ),
                        )
                        updated += 1
                    else:
                        cur.execute(
                            """
                            INSERT INTO destinations (
                                rag_place_id,
                                name,
                                description,
                                address,
                                city,
                                province,
                                latitude,
                                longitude,
                                category,
                                images_json,
                                rating,
                                review_count,
                                open_time,
                                close_time,
                                entry_fee,
                                tags_json
                            )
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """,
                            (
                                rag_place_id,
                                name,
                                description,
                                address,
                                city,
                                province,
                                latitude,
                                longitude,
                                category,
                                images_json,
                                rating,
                                review_count,
                                open_time,
                                close_time,
                                entry_fee,
                                tags_json,
                            ),
                        )
                        inserted += 1

        conn.commit()

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    print("[DONE] Import completed")
    print(f"Inserted: {inserted}")
    print(f"Updated : {updated}")
    print(f"Skipped : {skipped}")
    print(f"Total   : {inserted + updated + skipped}")


if __name__ == "__main__":
    import_places()