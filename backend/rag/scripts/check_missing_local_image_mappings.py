# -*- coding: utf-8 -*-
from pathlib import Path
import mysql.connector

ROOT = Path(r"E:\testmodelrag\smarttravel-rag-v2")
OPT = ROOT / "data" / "image_pipeline" / "downloaded" / "optimized"

conn = mysql.connector.connect(
    host="127.0.0.1",
    port=3306,
    user="root",
    password="",
    database="unudata",
    charset="utf8mb4",
    use_unicode=True,
)

cur = conn.cursor()
cur.execute("""
    SELECT rag_place_id
    FROM destinations
    WHERE rag_place_id IS NOT NULL
      AND rag_place_id != ''
""")

db_ids = {str(row[0]) for row in cur.fetchall()}

print("Missing local folders not in destinations:")

missing_count = 0
missing_images = 0

for folder in sorted(OPT.iterdir()):
    if not folder.is_dir():
        continue

    image_count = len(list(folder.glob("*.webp")))

    if folder.name not in db_ids:
        print(f"{folder.name} {image_count}")
        missing_count += 1
        missing_images += image_count

print("")
print(f"Missing folders: {missing_count}")
print(f"Missing images : {missing_images}")

cur.close()
conn.close()
