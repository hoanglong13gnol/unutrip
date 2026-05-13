# -*- coding: utf-8 -*-
"""
Import AI-generated image candidate CSV into destination_image_candidates.

Input CSV columns:
  rag_place_id,place_name,image_url,source_page_url,source,credit,license_note,
  image_order,is_primary,batch_code,provider,confidence,need_human_check,
  candidate_status,ai_note

This script only writes to:
  destination_image_candidates

It does NOT write to:
  destination_images
  destinations.images_json
"""

import argparse
import csv
import os
from pathlib import Path

import mysql.connector


ROOT_DIR = Path(__file__).resolve().parents[1]


BLOCKED_PATTERNS = [
    "picsum.photos",
    "source.unsplash.com/random",
    "placehold.co",
    "dummyimage",
    "loremflickr",
]


def clean(value):
    if value is None:
        return ""
    return str(value).replace("\r", " ").replace("\n", " ").strip()


def to_int(value, default=0):
    text = clean(value).lower()
    if text in ("1", "true", "yes", "y"):
        return 1
    if text in ("0", "false", "no", "n"):
        return 0
    try:
        return int(float(text))
    except Exception:
        return default


def is_blocked_url(url):
    text = clean(url).lower()
    if not text:
        return False
    return any(pattern in text for pattern in BLOCKED_PATTERNS)


def connect(args):
    return mysql.connector.connect(
        host=args.db_host,
        port=args.db_port,
        user=args.db_user,
        password=args.db_password,
        database=args.db_name,
        charset="utf8mb4",
        use_unicode=True,
    )


def get_destination(cur, rag_place_id):
    cur.execute(
        """
        SELECT id, name
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
        "name": row[1],
    }


def candidate_exists(cur, rag_place_id, image_url, source_page_url):
    cur.execute(
        """
        SELECT id
        FROM destination_image_candidates
        WHERE rag_place_id = %s
          AND COALESCE(image_url, '') = %s
          AND COALESCE(source_page_url, '') = %s
        LIMIT 1
        """,
        (
            rag_place_id,
            clean(image_url),
            clean(source_page_url),
        ),
    )
    return cur.fetchone() is not None


def import_candidates(args):
    input_path = Path(args.input)
    if not input_path.is_absolute():
        input_path = ROOT_DIR / input_path

    if not input_path.exists():
        raise FileNotFoundError(f"Input CSV not found: {input_path}")

    conn = connect(args)
    cur = conn.cursor()

    inserted = 0
    skipped_missing_place = 0
    skipped_duplicate = 0
    skipped_blocked = 0
    skipped_bad_row = 0

    try:
        with input_path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)

            required_cols = {
                "rag_place_id",
                "place_name",
                "image_url",
                "source_page_url",
                "source",
                "credit",
                "license_note",
                "image_order",
                "is_primary",
                "batch_code",
                "provider",
                "confidence",
                "need_human_check",
                "candidate_status",
                "ai_note",
            }

            missing = required_cols - set(reader.fieldnames or [])
            if missing:
                raise ValueError(f"CSV missing columns: {sorted(missing)}")

            for row_no, row in enumerate(reader, start=2):
                rag_place_id = clean(row.get("rag_place_id"))
                if not rag_place_id:
                    skipped_bad_row += 1
                    print(f"[SKIP BAD ROW] line {row_no}: missing rag_place_id")
                    continue

                image_url = clean(row.get("image_url"))
                source_page_url = clean(row.get("source_page_url"))

                if is_blocked_url(image_url) or is_blocked_url(source_page_url):
                    skipped_blocked += 1
                    print(f"[SKIP BLOCKED] {rag_place_id}: {image_url or source_page_url}")
                    continue

                dest = get_destination(cur, rag_place_id)
                if not dest:
                    skipped_missing_place += 1
                    print(f"[SKIP MISSING PLACE] {rag_place_id}")
                    continue

                if candidate_exists(cur, rag_place_id, image_url, source_page_url):
                    skipped_duplicate += 1
                    continue

                place_name = clean(row.get("place_name")) or dest["name"]
                candidate_status = clean(row.get("candidate_status")) or "pending"

                cur.execute(
                    """
                    INSERT INTO destination_image_candidates (
                        destination_id,
                        rag_place_id,
                        place_name,
                        image_url,
                        source_page_url,
                        source,
                        credit,
                        license_note,
                        image_order,
                        is_primary,
                        batch_code,
                        provider,
                        confidence,
                        need_human_check,
                        candidate_status,
                        ai_note
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        dest["id"],
                        rag_place_id,
                        place_name,
                        image_url or None,
                        source_page_url or None,
                        clean(row.get("source")) or None,
                        clean(row.get("credit")) or None,
                        clean(row.get("license_note")) or None,
                        to_int(row.get("image_order"), default=1),
                        to_int(row.get("is_primary"), default=0),
                        clean(row.get("batch_code")) or args.batch_code,
                        clean(row.get("provider")) or "ai_batch",
                        clean(row.get("confidence")) or None,
                        to_int(row.get("need_human_check"), default=1),
                        candidate_status,
                        clean(row.get("ai_note")) or None,
                    ),
                )
                inserted += 1

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        cur.close()
        conn.close()

    print("[DONE] Import image candidates completed")
    print(f"Input CSV             : {input_path}")
    print(f"Inserted              : {inserted}")
    print(f"Skipped duplicate     : {skipped_duplicate}")
    print(f"Skipped missing place : {skipped_missing_place}")
    print(f"Skipped blocked URL   : {skipped_blocked}")
    print(f"Skipped bad row       : {skipped_bad_row}")


def parse_args():
    parser = argparse.ArgumentParser(description="Import image candidate CSV into MySQL.")

    parser.add_argument("--input", required=True, help="Path to candidate CSV.")
    parser.add_argument("--batch-code", default="", help="Fallback batch code.")

    parser.add_argument("--db-host", default=os.getenv("DB_HOST", "127.0.0.1"))
    parser.add_argument("--db-port", type=int, default=int(os.getenv("DB_PORT", "3306")))
    parser.add_argument("--db-user", default=os.getenv("DB_USER", "root"))
    parser.add_argument("--db-password", default=os.getenv("DB_PASSWORD", ""))
    parser.add_argument("--db-name", default=os.getenv("DB_NAME", "unudata"))

    return parser.parse_args()


if __name__ == "__main__":
    import_candidates(parse_args())
