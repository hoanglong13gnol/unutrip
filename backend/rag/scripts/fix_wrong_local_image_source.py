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
    UPDATE destinations
    SET image_source = 'external_existing'
    WHERE image_source = 'local_downloaded_tier_1_2'
      AND images_json LIKE '%http%'
      AND images_json NOT LIKE '%/images/destinations/%'
""")

conn.commit()

print("fixed rows:", cur.rowcount)

cur.close()
conn.close()
