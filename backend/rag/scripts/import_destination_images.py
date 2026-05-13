# -*- coding: utf-8 -*-
"""
Import real destination images from CSV into MySQL.

Input:
  data/image_updates.csv

CSV columns:
  rag_place_id,image_url,source,credit,license_note,is_primary,status

Rules:
  - Skip rows with empty image_url
  - Skip placeholder/random image URLs
  - Find destination by rag_place_id
  - Insert into destination_images
  - Refresh destinations.images_json cache from active images
"""

import csv
import json
import os
import sys
from pathlib import Path

import mysql.connector


MYSQL_HOST = os.getenv("DB_HOST", "127.0.0.1")
MYSQL_PORT = int(os.getenv("DB_PORT", "3306"))
MYSQL_USER = os.getenv("DB_USER", "root")
MYSQL_PASSWORD = os.getenv("DB_PASSWORD", "")
MYSQL_DB = os.getenv("DB_NAME", "unudata")

ROOT_DIR = Path(__file__).resolve().parents[1]
INPUT_FILE = ROOT_DIR / "data" / "image_updates.csv"


BLOCKED_IMAGE_PATTERNS = [
    "picsum.photos",
    "source.unsplash.com/random",
    "placehold.co",
    "dummyimage",
    "loremflickr",
    "example.com",
]


def clean(value):
    if value is None:
        return ""
    return str(value).strip()


def to_int_bool(value, default=0):
    text = clean(value).lower()
    if text in ("1", "true", "yes", "y"):
        return 1
    if text in ("0", "false", "no", "n"):
        return 0
    return default


def is_blocked_url(url):
    low = url.lower()
    return any(pattern in low for pattern in BLOCKED_IMAGE_PATTERNS)


def connect():
    return mysql.connector.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DB,
        charset="utf8mb4",
        use_unicode=True,
    )


def get_destination(cur, rag_place_id):
    cur.execute(
        """
        SELECT id, rag_place_id, name
        FROM destinations
        WHERE rag_place_id = %s
        LIMIT 1
        """,
        (rag_place_id,),
    )
    row = cur.fetchone()
    if not row:
        return None

    return {
        "id": row[0],
        "rag_place_id": row[1],
        "name": row[2],
    }


def image_exists(cur, destination_id, image_url):
    cur.execute(
        """
        SELECT id
        FROM destination_images
        WHERE destination_id = %s
          AND image_url = %s
        LIMIT 1
        """,
        (destination_id, image_url),
    )
    return cur.fetchone() is not None


def refresh_images_cache(cur, destination_id):
    cur.execute(
        """
        SELECT image_url
        FROM destination_images
        WHERE destination_id = %s
          AND status = 'active'
        ORDER BY is_primary DESC, id ASC
        """,
        (destination_id,),
    )

    urls = [row[0] for row in cur.fetchall()]
    images_json = json.dumps(urls, ensure_ascii=False)

    cur.execute(
        """
        UPDATE destinations
        SET images_json = %s
        WHERE id = %s
        """,
        (images_json, destination_id),
    )


def import_images():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Input file not found: {INPUT_FILE}")

    conn = connect()
    cur = conn.cursor()

    inserted = 0
    skipped_empty = 0
    skipped_blocked = 0
    skipped_missing_destination = 0
    skipped_duplicate = 0
    refreshed_destination_ids = set()

    try:
        with INPUT_FILE.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)

            required = {
                "rag_place_id",
                "image_url",
                "source",
                "credit",
                "license_note",
                "is_primary",
                "status",
            }

            missing_cols = required - set(reader.fieldnames or [])
            if missing_cols:
                raise ValueError(f"CSV missing columns: {sorted(missing_cols)}")

            for row in reader:
                rag_place_id = clean(row.get("rag_place_id"))
                image_url = clean(row.get("image_url"))

                if not rag_place_id or not image_url:
                    skipped_empty += 1
                    continue

                if is_blocked_url(image_url):
                    print(f"[SKIP BLOCKED] {rag_place_id}: {image_url}")
                    skipped_blocked += 1
                    continue

                dest = get_destination(cur, rag_place_id)
                if not dest:
                    print(f"[SKIP MISSING DESTINATION] {rag_place_id}")
                    skipped_missing_destination += 1
                    continue

                destination_id = dest["id"]

                if image_exists(cur, destination_id, image_url):
                    skipped_duplicate += 1
                    refreshed_destination_ids.add(destination_id)
                    continue

                source = clean(row.get("source")) or None
                credit = clean(row.get("credit")) or None
                license_note = clean(row.get("license_note")) or None
                is_primary = to_int_bool(row.get("is_primary"), default=0)
                status = clean(row.get("status")) or "active"

                cur.execute(
                    """
                    INSERT INTO destination_images (
                        destination_id,
                        rag_place_id,
                        image_url,
                        source,
                        credit,
                        license_note,
                        is_primary,
                        status
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        destination_id,
                        rag_place_id,
                        image_url,
                        source,
                        credit,
                        license_note,
                        is_primary,
                        status,
                    ),
                )

                inserted += 1
                refreshed_destination_ids.add(destination_id)

        for destination_id in refreshed_destination_ids:
            refresh_images_cache(cur, destination_id)

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        cur.close()
        conn.close()

    print("[DONE] Import destination images completed")
    print(f"Input file                  : {INPUT_FILE}")
    print(f"Inserted                    : {inserted}")
    print(f"Skipped empty URL           : {skipped_empty}")
    print(f"Skipped blocked/random URL  : {skipped_blocked}")
    print(f"Skipped missing destination : {skipped_missing_destination}")
    print(f"Skipped duplicate           : {skipped_duplicate}")
    print(f"Refreshed cache destinations: {len(refreshed_destination_ids)}")


if __name__ == "__main__":
    import_images()
