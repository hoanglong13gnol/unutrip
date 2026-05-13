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
    UPDATE destinations d
    JOIN priority_place_tiers p ON p.rag_place_id = d.rag_place_id
    SET d.image_source = 'local_downloaded_tier_1_2'
    WHERE p.tier IN (1,2)
      AND d.images_json IS NOT NULL
      AND LENGTH(TRIM(d.images_json)) > 2
""")

conn.commit()

print("updated image_source rows:", cur.rowcount)

cur.close()
conn.close()
