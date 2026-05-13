# -*- coding: utf-8 -*-
"""
Soft priority score update.

- Does NOT touch images_json.
- Does NOT delete any destinations.
- Does NOT disable rag_places.
- Boosts only priority tier rows to minimum score/rating.
- Lowers non-priority rows by 1 point only.

Tables affected:
  destinations.rating
  rag_places.quality_score
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

print("Checking priority_place_tiers...")
cur.execute("SELECT COUNT(*) FROM priority_place_tiers")
print("priority_place_tiers rows:", cur.fetchone()[0])

print("Updating destinations.rating softly...")

cur.execute("""
    UPDATE destinations d
    LEFT JOIN priority_place_tiers p
        ON p.rag_place_id = d.rag_place_id
    SET d.rating =
        CASE
            WHEN p.tier = 1 THEN GREATEST(COALESCE(d.rating, 0), 4.8)
            WHEN p.tier = 2 THEN GREATEST(COALESCE(d.rating, 0), 4.6)
            WHEN p.tier = 3 THEN GREATEST(COALESCE(d.rating, 0), 4.4)
            WHEN p.tier = 4 THEN GREATEST(COALESCE(d.rating, 0), 4.2)
            ELSE GREATEST(COALESCE(d.rating, 3.0) - 1.0, 1.0)
        END
""")

print("destinations updated:", cur.rowcount)

print("Updating rag_places.quality_score softly...")

cur.execute("""
    UPDATE rag_places r
    LEFT JOIN priority_place_tiers p
        ON p.rag_place_id = r.place_id
    SET r.quality_score =
        CASE
            WHEN p.tier = 1 THEN GREATEST(COALESCE(r.quality_score, 0), 9.5)
            WHEN p.tier = 2 THEN GREATEST(COALESCE(r.quality_score, 0), 9.0)
            WHEN p.tier = 3 THEN GREATEST(COALESCE(r.quality_score, 0), 8.5)
            WHEN p.tier = 4 THEN GREATEST(COALESCE(r.quality_score, 0), 8.0)
            ELSE GREATEST(COALESCE(r.quality_score, 4.0) - 1.0, 0.0)
        END
""")

print("rag_places updated:", cur.rowcount)

conn.commit()

print("")
print("Done. images_json was NOT modified.")

print("")
print("Destination rating distribution:")
cur.execute("""
    SELECT rating, COUNT(*)
    FROM destinations
    GROUP BY rating
    ORDER BY rating DESC
""")
for row in cur.fetchall():
    print(row)

print("")
print("RAG quality_score distribution:")
cur.execute("""
    SELECT quality_score, COUNT(*)
    FROM rag_places
    GROUP BY quality_score
    ORDER BY quality_score DESC
    LIMIT 30
""")
for row in cur.fetchall():
    print(row)

cur.close()
conn.close()
