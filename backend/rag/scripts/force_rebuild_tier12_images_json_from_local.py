# -*- coding: utf-8 -*-
"""
Force rebuild destinations.images_json from local backend webp files.

Source:
  E:/testmodelrag/unutrip/backend/public/images/destinations/<rag_place_id>/*.webp

Target:
  destinations.images_json = JSON array of local public URLs
  destinations.image_source = local_downloaded_tier_1_2

Scope:
  Only priority_place_tiers tier 1 and 2
  Only places that actually have local .webp files

Does NOT touch:
  rag_places
  rating
  quality_score
  destination_images
"""

import csv
import json
from datetime import datetime
from pathlib import Path

import mysql.connector


BACKEND_IMAGE_DIR = Path(r"E:\testmodelrag\unutrip\backend\public\images\destinations")
BACKUP_DIR = Path(r"E:\testmodelrag\smarttravel-rag-v2\data\image_pipeline\backup\force_rebuild_images_json")
PUBLIC_PREFIX = "/images/destinations"
SOURCE_VALUE = "local_downloaded_tier_1_2"


def now_stamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def connect():
    return mysql.connector.connect(
        host="127.0.0.1",
        port=3306,
        user="root",
        password="",
        database="unudata",
        charset="utf8mb4",
        use_unicode=True,
    )


def backup_rows(cur, rows):
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    path = BACKUP_DIR / f"destinations_before_force_rebuild_images_json_{now_stamp()}.csv"

    ids = [r["rag_place_id"] for r in rows]

    if not ids:
        return path, 0

    placeholders = ",".join(["%s"] * len(ids))

    cur.execute(f"""
        SELECT *
        FROM destinations
        WHERE rag_place_id IN ({placeholders})
    """, ids)

    data = cur.fetchall()
    cols = [d[0] for d in cur.description]

    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(cols)
        writer.writerows(data)

    return path, len(data)


def main():
    conn = connect()
    cur = conn.cursor(dictionary=True)

    cur.execute("""
        SELECT d.id, d.rag_place_id, d.name, p.tier
        FROM destinations d
        JOIN priority_place_tiers p ON p.rag_place_id = d.rag_place_id
        WHERE p.tier IN (1, 2)
    """)

    tier_rows = cur.fetchall()

    updates = []

    for row in tier_rows:
        rid = str(row["rag_place_id"])
        folder = BACKEND_IMAGE_DIR / rid

        if not folder.exists():
            continue

        files = sorted(folder.glob("*.webp"))

        if not files:
            continue

        urls = [
            f"{PUBLIC_PREFIX}/{rid}/{f.name}"
            for f in files
        ]

        updates.append({
            "rag_place_id": rid,
            "name": row["name"],
            "tier": row["tier"],
            "urls": urls,
        })

    print("Tier 1+2 rows:", len(tier_rows))
    print("Places with local .webp:", len(updates))
    print("Total local image urls:", sum(len(r["urls"]) for r in updates))

    print("")
    print("Sample:")
    for row in updates[:10]:
        print(row["rag_place_id"], "|", row["name"], "|", row["tier"], "|", len(row["urls"]), "images")
        print(" ", row["urls"][0])

    backup_path, backup_count = backup_rows(cur, updates)

    for row in updates:
        cur.execute("""
            UPDATE destinations
            SET images_json = %s,
                image_source = %s
            WHERE rag_place_id = %s
        """, (
            json.dumps(row["urls"], ensure_ascii=False),
            SOURCE_VALUE,
            row["rag_place_id"],
        ))

    conn.commit()

    print("")
    print("FORCE REBUILD DONE.")
    print("Backup:", backup_path)
    print("Backup rows:", backup_count)
    print("Updated places:", len(updates))

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
