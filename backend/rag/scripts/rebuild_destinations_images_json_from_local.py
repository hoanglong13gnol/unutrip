# -*- coding: utf-8 -*-
"""
Rebuild destinations.images_json from downloaded local webp images.

Purpose:
  - Update destinations.images_json from backend public image files.
  - Optionally update destinations.image_source ONLY IF destinations.image_image_source column exists.
  - Filter to priority tiers 1 and 2 by default.
  - Does NOT touch rag_places.
  - Does NOT change rating/score.
  - Does NOT delete destination_images.
  - Dry-run by default. Use --execute to write DB.

Image source folder:
  E:/testmodelrag/unutrip/backend/public/images/destinations/<rag_place_id>/*.webp

images_json format:
  JSON array of public URLs:
  [
    "/images/destinations/AG_0001/AG_0001_01.webp",
    "/images/destinations/AG_0001/AG_0001_02.webp"
  ]
"""

import argparse
import csv
import json
import os
from datetime import datetime
from pathlib import Path

import mysql.connector


DEFAULT_BACKEND_IMAGE_DIR = Path(r"E:\testmodelrag\unutrip\backend\public\images\destinations")
DEFAULT_BACKUP_DIR = Path(r"E:\testmodelrag\smarttravel-rag-v2\data\image_pipeline\backup\rebuild_images_json")


def now_stamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


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


def table_exists(cur, table_name):
    cur.execute("SHOW TABLES LIKE %s", (table_name,))
    return cur.fetchone() is not None


def get_columns(cur, table_name):
    cur.execute(f"DESCRIBE {table_name}")
    return [row[0] for row in cur.fetchall()]


def backup_destinations_subset(cur, rag_place_ids, backup_dir):
    backup_dir.mkdir(parents=True, exist_ok=True)
    out_path = backup_dir / f"destinations_images_json_backup_{now_stamp()}.csv"

    if not rag_place_ids:
        return out_path, 0

    placeholders = ",".join(["%s"] * len(rag_place_ids))
    sql = f"""
        SELECT *
        FROM destinations
        WHERE rag_place_id IN ({placeholders})
    """
    cur.execute(sql, list(rag_place_ids))

    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]

    with out_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(cols)
        writer.writerows(rows)

    return out_path, len(rows)


def load_allowed_tier_ids(cur, tiers):
    if not table_exists(cur, "priority_place_tiers"):
        raise RuntimeError("priority_place_tiers table not found. Create it first.")

    placeholders = ",".join(["%s"] * len(tiers))
    sql = f"""
        SELECT rag_place_id, tier
        FROM priority_place_tiers
        WHERE tier IN ({placeholders})
    """
    cur.execute(sql, tiers)

    result = {}
    for rid, tier in cur.fetchall():
        result[str(rid)] = int(tier)

    return result


def load_destination_ids(cur):
    cur.execute("""
        SELECT id, rag_place_id, name
        FROM destinations
        WHERE rag_place_id IS NOT NULL
          AND rag_place_id != ''
    """)

    result = {}
    for did, rid, name in cur.fetchall():
        result[str(rid)] = {
            "id": did,
            "rag_place_id": str(rid),
            "name": str(name or ""),
        }

    return result


def scan_public_images(image_dir, public_prefix, allowed_ids):
    image_dir = Path(image_dir)

    if not image_dir.exists():
        raise FileNotFoundError(f"Backend image dir not found: {image_dir}")

    rows = {}

    for place_dir in sorted([p for p in image_dir.iterdir() if p.is_dir()]):
        rid = place_dir.name

        if rid not in allowed_ids:
            continue

        files = sorted(place_dir.glob("*.webp"))

        if not files:
            continue

        urls = [
            f"{public_prefix.rstrip('/')}/{rid}/{f.name}"
            for f in files
        ]

        rows[rid] = urls

    return rows


def print_schema_info(dest_cols):
    print("destinations columns detected:")
    print(", ".join(dest_cols))
    print("")
    print("Will update:")
    print("  - destinations.images_json")

    if "image_source" in dest_cols:
        print("  - destinations.image_source")
    else:
        print("  - destinations.image_source: SKIP because column does not exist")


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--tiers", nargs="+", type=int, default=[1, 2])
    parser.add_argument("--backend-image-dir", default=str(DEFAULT_BACKEND_IMAGE_DIR))
    parser.add_argument("--public-prefix", default="/images/destinations")
    parser.add_argument("--source-value", default="local_downloaded_tier_1_2")
    parser.add_argument("--backup-dir", default=str(DEFAULT_BACKUP_DIR))

    parser.add_argument("--db-host", default=os.getenv("DB_HOST", "127.0.0.1"))
    parser.add_argument("--db-port", type=int, default=int(os.getenv("DB_PORT", "3306")))
    parser.add_argument("--db-user", default=os.getenv("DB_USER", "root"))
    parser.add_argument("--db-password", default=os.getenv("DB_PASSWORD", ""))
    parser.add_argument("--db-name", default=os.getenv("DB_NAME", "unudata"))

    args = parser.parse_args()

    conn = connect(args)
    cur = conn.cursor()

    if not table_exists(cur, "destinations"):
        raise RuntimeError("destinations table not found")

    dest_cols = get_columns(cur, "destinations")

    if "rag_place_id" not in dest_cols:
        raise RuntimeError("destinations.rag_place_id not found")

    if "images_json" not in dest_cols:
        raise RuntimeError("destinations.images_json not found")

    print_schema_info(dest_cols)

    allowed_ids = load_allowed_tier_ids(cur, args.tiers)
    db_destinations = load_destination_ids(cur)
    local_images = scan_public_images(
        image_dir=args.backend_image_dir,
        public_prefix=args.public_prefix,
        allowed_ids=allowed_ids,
    )

    matched = {}
    missing_in_db = []
    no_local_images = []

    for rid in sorted(allowed_ids.keys()):
        if rid not in db_destinations:
            missing_in_db.append(rid)
            continue

        urls = local_images.get(rid, [])

        if not urls:
            no_local_images.append(rid)
            continue

        matched[rid] = urls

    total_images = sum(len(v) for v in matched.values())

    print("")
    print("Plan:")
    print(f"  Tiers selected        : {args.tiers}")
    print(f"  Tier place ids        : {len(allowed_ids)}")
    print(f"  Places with local imgs: {len(matched)}")
    print(f"  Total image URLs      : {total_images}")
    print(f"  Missing in DB         : {len(missing_in_db)}")
    print(f"  Tier places no images : {len(no_local_images)}")

    print("")
    print("Sample updates:")
    for rid in list(sorted(matched.keys()))[:10]:
        name = db_destinations[rid]["name"]
        print(f"  {rid} | {name} | {len(matched[rid])} images")
        print(f"    {matched[rid][0]}")

    if not args.execute:
        print("")
        print("DRY RUN ONLY. No DB changes.")
        print("Run with --execute to update destinations.images_json.")
        cur.close()
        conn.close()
        return

    backup_path, backup_count = backup_destinations_subset(
        cur=cur,
        rag_place_ids=list(matched.keys()),
        backup_dir=Path(args.backup_dir),
    )

    updated = 0

    has_source_col = "source" in dest_cols

    for rid, urls in matched.items():
        images_json = json.dumps(urls, ensure_ascii=False)

        if has_source_col:
            cur.execute("""
                UPDATE destinations
                SET images_json = %s,
                    image_source = %s
                WHERE rag_place_id = %s
            """, (images_json, args.source_value, rid))
        else:
            cur.execute("""
                UPDATE destinations
                SET images_json = %s
                WHERE rag_place_id = %s
            """, (images_json, rid))

        updated += cur.rowcount

    conn.commit()

    print("")
    print("UPDATE DONE.")
    print(f"Backup file     : {backup_path}")
    print(f"Backup rows     : {backup_count}")
    print(f"Updated places  : {updated}")
    print(f"Total images    : {total_images}")
    print("rag_places was NOT modified.")
    print("rating/score was NOT modified.")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
