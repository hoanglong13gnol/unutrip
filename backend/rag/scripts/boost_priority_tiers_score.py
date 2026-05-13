# -*- coding: utf-8 -*-
"""
Boost priority tiers and lower non-priority destinations.

Input:
  data/image_pipeline/priority_matched/tier_1_url_template.csv
  data/image_pipeline/priority_matched/tier_2_url_template.csv
  data/image_pipeline/priority_matched/tier_3_url_template.csv
  data/image_pipeline/priority_matched/tier_4_url_template.csv

DB effects when --execute:
  - Create/replace priority_place_tiers
  - Update destinations.rating/review_count
  - Update rag_places.quality_score/recommended_use

Safe:
  - Dry-run by default
  - Creates CSV backups before update
"""

import argparse
import csv
import os
from datetime import datetime
from pathlib import Path

import mysql.connector


ROOT_DIR = Path(__file__).resolve().parents[1]
MATCHED_DIR = ROOT_DIR / "data" / "image_pipeline" / "priority_matched"
BACKUP_DIR = ROOT_DIR / "data" / "image_pipeline" / "backup" / "priority_score_update"


TIER_CONFIG = {
    1: {"rating": 4.9, "review_count": 980, "quality_score": 9.8, "recommended_use": "main"},
    2: {"rating": 4.7, "review_count": 720, "quality_score": 9.2, "recommended_use": "main"},
    3: {"rating": 4.5, "review_count": 480, "quality_score": 8.6, "recommended_use": "supporting"},
    4: {"rating": 4.3, "review_count": 260, "quality_score": 8.0, "recommended_use": "supporting"},
}

NON_PRIORITY = {
    "rating": 2.0,
    "review_count": 5,
    "quality_score": 3.0,
    "recommended_use": "supporting",
}


def now_stamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def clean(value):
    if value is None:
        return ""
    return str(value).strip()


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


def table_exists(cur, table):
    cur.execute("SHOW TABLES LIKE %s", (table,))
    return cur.fetchone() is not None


def get_columns(cur, table):
    cur.execute(f"DESCRIBE {table}")
    return {row[0] for row in cur.fetchall()}


def backup_table(cur, table):
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    out_path = BACKUP_DIR / f"{table}_before_priority_score_{now_stamp()}.csv"

    cur.execute(f"SELECT * FROM {table}")
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]

    with out_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(cols)
        writer.writerows(rows)

    return out_path, len(rows)


def read_tier_files():
    rows = []
    seen = {}

    for tier in [1, 2, 3, 4]:
        path = MATCHED_DIR / f"tier_{tier}_url_template.csv"

        if not path.exists():
            print(f"[WARN] Missing tier file: {path}")
            continue

        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)

            for row in reader:
                rid = clean(row.get("id"))
                name = clean(row.get("name"))
                province = clean(row.get("province"))

                if not rid:
                    continue

                # If duplicate appears across tiers, keep smaller tier number.
                if rid in seen:
                    old = seen[rid]
                    if tier < old["tier"]:
                        old.update({"tier": tier, "name": name, "province": province})
                    continue

                seen[rid] = {
                    "rag_place_id": rid,
                    "tier": tier,
                    "name": name,
                    "province": province,
                }

    rows = list(seen.values())
    rows.sort(key=lambda x: (x["tier"], x["rag_place_id"]))
    return rows


def create_priority_table(cur, rows):
    cur.execute("DROP TABLE IF EXISTS priority_place_tiers")

    cur.execute("""
        CREATE TABLE priority_place_tiers (
            rag_place_id VARCHAR(50) NOT NULL PRIMARY KEY,
            tier INT NOT NULL,
            name VARCHAR(500) NULL,
            province VARCHAR(255) NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    for row in rows:
        cur.execute("""
            INSERT INTO priority_place_tiers (rag_place_id, tier, name, province)
            VALUES (%s, %s, %s, %s)
        """, (
            row["rag_place_id"],
            row["tier"],
            row["name"],
            row["province"],
        ))


def count_matches(cur):
    cur.execute("""
        SELECT p.tier, COUNT(*)
        FROM priority_place_tiers p
        JOIN destinations d ON d.rag_place_id = p.rag_place_id
        GROUP BY p.tier
        ORDER BY p.tier
    """)
    dest_counts = cur.fetchall()

    cur.execute("""
        SELECT p.tier, COUNT(*)
        FROM priority_place_tiers p
        JOIN rag_places r ON r.place_id = p.rag_place_id
        GROUP BY p.tier
        ORDER BY p.tier
    """)
    rag_counts = cur.fetchall()

    cur.execute("""
        SELECT COUNT(*)
        FROM priority_place_tiers p
        LEFT JOIN destinations d ON d.rag_place_id = p.rag_place_id
        WHERE d.id IS NULL
    """)
    missing_dest = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*)
        FROM priority_place_tiers p
        LEFT JOIN rag_places r ON r.place_id = p.rag_place_id
        WHERE r.id IS NULL
    """)
    missing_rag = cur.fetchone()[0]

    return dest_counts, rag_counts, missing_dest, missing_rag


def update_destinations(cur):
    # Lower all non-priority.
    cur.execute("""
        UPDATE destinations d
        LEFT JOIN priority_place_tiers p ON p.rag_place_id = d.rag_place_id
        SET
            d.rating = CASE
                WHEN p.tier = 1 THEN 4.9
                WHEN p.tier = 2 THEN 4.7
                WHEN p.tier = 3 THEN 4.5
                WHEN p.tier = 4 THEN 4.3
                ELSE 2.0
            END,
            d.review_count = CASE
                WHEN p.tier = 1 THEN 980
                WHEN p.tier = 2 THEN 720
                WHEN p.tier = 3 THEN 480
                WHEN p.tier = 4 THEN 260
                ELSE 5
            END
    """)
    return cur.rowcount


def update_rag_places(cur):
    cur.execute("""
        UPDATE rag_places r
        LEFT JOIN priority_place_tiers p ON p.rag_place_id = r.place_id
        SET
            r.quality_score = CASE
                WHEN p.tier = 1 THEN 9.8
                WHEN p.tier = 2 THEN 9.2
                WHEN p.tier = 3 THEN 8.6
                WHEN p.tier = 4 THEN 8.0
                ELSE 3.0
            END,
            r.recommended_use = CASE
                WHEN p.tier = 1 THEN 'main'
                WHEN p.tier = 2 THEN 'main'
                WHEN p.tier = 3 THEN 'supporting'
                WHEN p.tier = 4 THEN 'supporting'
                ELSE 'supporting'
            END,
            r.recommended_use_norm = CASE
                WHEN p.tier = 1 THEN 'main'
                WHEN p.tier = 2 THEN 'main'
                WHEN p.tier = 3 THEN 'supporting'
                WHEN p.tier = 4 THEN 'supporting'
                ELSE 'supporting'
            END
    """)
    return cur.rowcount


def print_top_checks(cur):
    print("")
    print("Top destinations by rating:")
    cur.execute("""
        SELECT d.rag_place_id, d.name, d.province, d.rating, d.review_count, p.tier
        FROM destinations d
        LEFT JOIN priority_place_tiers p ON p.rag_place_id = d.rag_place_id
        ORDER BY d.rating DESC, d.review_count DESC
        LIMIT 20
    """)
    for row in cur.fetchall():
        print(row)

    print("")
    print("Top rag_places by quality_score:")
    cur.execute("""
        SELECT r.place_id, r.name, r.province, r.quality_score, r.recommended_use, p.tier
        FROM rag_places r
        LEFT JOIN priority_place_tiers p ON p.rag_place_id = r.place_id
        ORDER BY r.quality_score DESC
        LIMIT 20
    """)
    for row in cur.fetchall():
        print(row)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--db-host", default=os.getenv("DB_HOST", "127.0.0.1"))
    parser.add_argument("--db-port", type=int, default=int(os.getenv("DB_PORT", "3306")))
    parser.add_argument("--db-user", default=os.getenv("DB_USER", "root"))
    parser.add_argument("--db-password", default=os.getenv("DB_PASSWORD", ""))
    parser.add_argument("--db-name", default=os.getenv("DB_NAME", "unudata"))
    args = parser.parse_args()

    tier_rows = read_tier_files()

    print(f"Priority tier rows loaded: {len(tier_rows)}")
    for tier in [1, 2, 3, 4]:
        print(f"Tier {tier}: {sum(1 for r in tier_rows if r['tier'] == tier)}")

    conn = connect(args)
    cur = conn.cursor()

    if not table_exists(cur, "destinations"):
        raise RuntimeError("destinations table not found")
    if not table_exists(cur, "rag_places"):
        raise RuntimeError("rag_places table not found")

    dest_cols = get_columns(cur, "destinations")
    rag_cols = get_columns(cur, "rag_places")

    if "rating" not in dest_cols:
        raise RuntimeError("destinations.rating not found")
    if "quality_score" not in rag_cols:
        raise RuntimeError("rag_places.quality_score not found")

    if not args.execute:
        print("")
        print("DRY RUN ONLY.")
        print("This will create priority_place_tiers and update rating/quality_score when --execute is used.")
        cur.close()
        conn.close()
        return

    backup_dest, dest_count = backup_table(cur, "destinations")
    backup_rag, rag_count = backup_table(cur, "rag_places")

    create_priority_table(cur, tier_rows)

    dest_counts, rag_counts, missing_dest, missing_rag = count_matches(cur)

    print("")
    print("Priority matches in destinations:", dest_counts)
    print("Priority matches in rag_places:", rag_counts)
    print("Missing destinations:", missing_dest)
    print("Missing rag_places:", missing_rag)

    updated_dest = update_destinations(cur)
    updated_rag = update_rag_places(cur)

    conn.commit()

    print("")
    print("UPDATE DONE.")
    print(f"Backup destinations: {backup_dest} ({dest_count} rows)")
    print(f"Backup rag_places  : {backup_rag} ({rag_count} rows)")
    print(f"Updated destinations rows: {updated_dest}")
    print(f"Updated rag_places rows  : {updated_rag}")

    print_top_checks(cur)

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
