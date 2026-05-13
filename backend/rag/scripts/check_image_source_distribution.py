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
    SELECT image_source, COUNT(*)
    FROM destinations
    WHERE image_source IS NOT NULL
      AND image_source != ''
    GROUP BY image_source
    ORDER BY COUNT(*) DESC
""")

for row in cur.fetchall():
    print(row)

cur.close()
conn.close()
