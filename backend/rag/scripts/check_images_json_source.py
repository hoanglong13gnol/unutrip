# -*- coding: utf-8 -*-
import mysql.connector

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
    SELECT COUNT(*)
    FROM destinations d
    JOIN priority_place_tiers p ON p.rag_place_id = d.rag_place_id
    WHERE p.tier IN (1,2)
      AND d.images_json IS NOT NULL
      AND LENGTH(TRIM(d.images_json)) > 2
""")
print("tier 1+2 with images_json:", cur.fetchone()[0])

cur.execute("""
    SELECT COUNT(*)
    FROM destinations
    WHERE image_source = 'local_downloaded_tier_1_2'
""")
print("image_source local_downloaded_tier_1_2:", cur.fetchone()[0])

cur.execute("""
    SELECT image_source, COUNT(*)
    FROM destinations
    WHERE image_source IS NOT NULL
      AND image_source != ''
    GROUP BY image_source
    ORDER BY COUNT(*) DESC
""")
print("")
print("image_source distribution:")
for row in cur.fetchall():
    print(row)

cur.execute("""
    SELECT d.rag_place_id, d.name, d.images_json, d.image_source
    FROM destinations d
    JOIN priority_place_tiers p ON p.rag_place_id = d.rag_place_id
    WHERE p.tier IN (1,2)
      AND d.images_json IS NOT NULL
      AND LENGTH(TRIM(d.images_json)) > 2
    LIMIT 10
""")

print("")
print("Sample:")
for rid, name, images_json, image_source in cur.fetchall():
    print(rid, "|", name, "|", str(images_json)[:120], "|", image_source)

cur.close()
conn.close()
