# -*- coding: utf-8 -*-
import csv
import os
from pathlib import Path
import mysql.connector

ROOT_DIR = Path(__file__).resolve().parents[1]
MATCHED_DIR = ROOT_DIR / "data" / "image_pipeline" / "priority_matched"

def clean(v):
    return "" if v is None else str(v).strip()

conn = mysql.connector.connect(
    host=os.getenv("DB_HOST", "127.0.0.1"),
    port=int(os.getenv("DB_PORT", "3306")),
    user=os.getenv("DB_USER", "root"),
    password=os.getenv("DB_PASSWORD", ""),
    database=os.getenv("DB_NAME", "unudata"),
    charset="utf8mb4",
    use_unicode=True,
)

rows = {}

for tier in [1, 2, 3, 4]:
    path = MATCHED_DIR / f"tier_{tier}_url_template.csv"

    if not path.exists():
        print(f"[WARN] Missing {path}")
        continue

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)

        for r in reader:
            rid = clean(r.get("id"))

            if not rid:
                continue

            if rid not in rows or tier < rows[rid]["tier"]:
                rows[rid] = {
                    "rag_place_id": rid,
                    "tier": tier,
                    "name": clean(r.get("name")),
                    "province": clean(r.get("province")),
                }

cur = conn.cursor()

cur.execute("DROP TABLE IF EXISTS priority_place_tiers")

cur.execute("""
    CREATE TABLE priority_place_tiers (
        rag_place_id VARCHAR(100) NOT NULL PRIMARY KEY,
        tier INT NOT NULL,
        name VARCHAR(500) NULL,
        province VARCHAR(255) NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_tier (tier)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
""")

for r in rows.values():
    cur.execute("""
        INSERT INTO priority_place_tiers (rag_place_id, tier, name, province)
        VALUES (%s, %s, %s, %s)
    """, (r["rag_place_id"], r["tier"], r["name"], r["province"]))

conn.commit()

print("Created priority_place_tiers")
print(f"Total rows: {len(rows)}")

for tier in [1, 2, 3, 4]:
    print(f"Tier {tier}: {sum(1 for r in rows.values() if r['tier'] == tier)}")

cur.execute("""
    SELECT p.tier, COUNT(*)
    FROM priority_place_tiers p
    JOIN destinations d ON d.rag_place_id = p.rag_place_id
    GROUP BY p.tier
    ORDER BY p.tier
""")

print("Matched destinations:", cur.fetchall())

cur.close()
conn.close()
