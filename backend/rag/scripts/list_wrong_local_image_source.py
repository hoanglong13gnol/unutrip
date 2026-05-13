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
    SELECT rag_place_id, name, province, images_json, image_source
    FROM destinations
    WHERE image_source = 'local_downloaded_tier_1_2'
      AND images_json LIKE '%http%'
      AND images_json NOT LIKE '%/images/destinations/%'
    ORDER BY province, name
""")

rows = cur.fetchall()

print("Wrong local source rows:", len(rows))
for rid, name, province, images_json, image_source in rows:
    print(rid, "|", name, "|", province, "|", str(images_json)[:140], "|", image_source)

cur.close()
conn.close()
