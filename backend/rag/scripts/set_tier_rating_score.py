# -*- coding: utf-8 -*-
"""
Set tier priority rating/score.

Rules:
  Tier 1: destinations.rating = 4.9, rag_places.quality_score = 9.8
  Tier 2: destinations.rating = 4.8, rag_places.quality_score = 9.7
  Tier 3: destinations.rating = 4.7, rag_places.quality_score = 9.7
  Tier 4: destinations.rating = 4.6, rag_places.quality_score = 9.6

  Tier 0 / non-priority:
    destinations.rating random stable 3.8 - 4.4
    rag_places.quality_score random stable 7.0 - 9.0

Does NOT touch images_json.
Does NOT delete data.
Requires priority_place_tiers table.
"""

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

cur.execute("SELECT COUNT(*) FROM priority_place_tiers")
tier_count = cur.fetchone()[0]
print("priority_place_tiers rows:", tier_count)

# destinations.rating
# Non-tier stable pseudo-random:
# 3.8 + CRC32(rag_place_id) % 61 / 100 => 3.80 .. 4.40
cur.execute("""
    UPDATE destinations d
    LEFT JOIN priority_place_tiers p
        ON p.rag_place_id = d.rag_place_id
    SET d.rating =
        CASE
            WHEN p.tier = 1 THEN 4.9
            WHEN p.tier = 2 THEN 4.8
            WHEN p.tier = 3 THEN 4.7
            WHEN p.tier = 4 THEN 4.6
            ELSE ROUND(3.8 + (CRC32(COALESCE(d.rag_place_id, CAST(d.id AS CHAR))) % 61) / 100, 1)
        END
""")
print("destinations updated:", cur.rowcount)

# rag_places.quality_score
# Non-tier stable pseudo-random:
# 7.0 + CRC32(place_id) % 201 / 100 => 7.00 .. 9.00
cur.execute("""
    UPDATE rag_places r
    LEFT JOIN priority_place_tiers p
        ON p.rag_place_id = r.place_id
    SET r.quality_score =
        CASE
            WHEN p.tier = 1 THEN 9.8
            WHEN p.tier = 2 THEN 9.7
            WHEN p.tier = 3 THEN 9.7
            WHEN p.tier = 4 THEN 9.6
            ELSE ROUND(7.0 + (CRC32(COALESCE(r.place_id, CAST(r.id AS CHAR))) % 201) / 100, 1)
        END
""")
print("rag_places updated:", cur.rowcount)

conn.commit()

print("")
print("Destination rating distribution:")
cur.execute("""
    SELECT COALESCE(p.tier, 0) AS tier, d.rating, COUNT(*)
    FROM destinations d
    LEFT JOIN priority_place_tiers p ON p.rag_place_id = d.rag_place_id
    GROUP BY COALESCE(p.tier, 0), d.rating
    ORDER BY tier, d.rating DESC
""")
for row in cur.fetchall():
    print(row)

print("")
print("RAG quality_score distribution:")
cur.execute("""
    SELECT COALESCE(p.tier, 0) AS tier, r.quality_score, COUNT(*)
    FROM rag_places r
    LEFT JOIN priority_place_tiers p ON p.rag_place_id = r.place_id
    GROUP BY COALESCE(p.tier, 0), r.quality_score
    ORDER BY tier, r.quality_score DESC
""")
for row in cur.fetchall()[:80]:
    print(row)

cur.close()
conn.close()
