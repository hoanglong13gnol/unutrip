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
    FROM destinations
    WHERE image_source = 'local_downloaded_tier_1_2'
      AND images_json LIKE '%http%'
""")
print("local source but external http images_json:", cur.fetchone()[0])

cur.execute("""
    SELECT COUNT(*)
    FROM destinations
    WHERE image_source = 'local_downloaded_tier_1_2'
      AND images_json LIKE '%/images/destinations/%'
""")
print("local source with local images_json:", cur.fetchone()[0])

cur.execute("""
    SELECT rag_place_id, name, images_json, image_source
    FROM destinations
    WHERE image_source = 'local_downloaded_tier_1_2'
    LIMIT 10
""")

print("")
print("Sample:")
for rid, name, images_json, image_source in cur.fetchall():
    print(rid, "|", name, "|", str(images_json)[:160], "|", image_source)

cur.close()
conn.close()
