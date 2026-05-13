# -*- coding: utf-8 -*-
"""
Export simple clean image prompt batches.

Output columns only:
  id, name, province, area, short_description, category,
  source_url, aliases, image_query_1, image_query_2, image_query_3, avoid_note

This script only reads MySQL.
It does NOT write to database.
"""

import argparse
import csv
import math
import os
from pathlib import Path

import mysql.connector


ROOT_DIR = Path(__file__).resolve().parents[1]

OUTPUT_HEADER = [
    "id",
    "name",
    "province",
    "area",
    "short_description",
    "category",
    "source_url",
    "aliases",
    "image_query_1",
    "image_query_2",
    "image_query_3",
    "avoid_note",
]


def clean(value):
    if value is None:
        return ""
    return str(value).replace("\r", " ").replace("\n", " ").strip()


def connect(args):
    return mysql.connector.connect(
        host=args.db_host,
        port=args.db_port,
        user=args.db_user,
        password=args.db_password,
        database=args.db_name,
        charset="utf8mb4",
        use_unicode=True,
    )


def get_columns(cur, table_name):
    cur.execute(f"DESCRIBE {table_name}")
    return {row[0] for row in cur.fetchall()}


def safe_select_expr(table_alias, table_columns, col_name, output_name=None):
    if output_name is None:
        output_name = col_name
    if col_name in table_columns:
        return f"{table_alias}.{col_name} AS {output_name}"
    return f"NULL AS {output_name}"


def build_aliases(row):
    name = clean(row.get("name"))
    province = clean(row.get("province"))
    area = clean(row.get("area"))
    address = clean(row.get("address"))

    aliases = []

    if name:
        aliases.append(name)

    if name and area and area not in name:
        aliases.append(f"{name} {area}")

    if name and province and province not in name:
        aliases.append(f"{name} {province}")

    if name and area and province:
        aliases.append(f"{name} {area} {province}")

    if address and name not in address:
        aliases.append(f"{name} {address}")

    result = []
    seen = set()

    for item in aliases:
        item = clean(item)
        key = item.lower()
        if item and key not in seen:
            result.append(item)
            seen.add(key)

    return " | ".join(result)


def build_queries(row):
    name = clean(row.get("name"))
    province = clean(row.get("province"))
    area = clean(row.get("area"))
    category = clean(row.get("category"))

    place_parts = [name]

    if area and area not in name:
        place_parts.append(area)

    if province and province not in name:
        place_parts.append(province)

    full_place = " ".join([x for x in place_parts if x]).strip()

    q1 = f'{full_place} ảnh'
    q2 = f'{full_place} hình ảnh du lịch'
    q3 = f'{full_place} jpg OR jpeg OR png OR webp'

    if category:
        q2 = f'{full_place} {category} ảnh'

    return q1, q2, q3


def build_avoid_note(row):
    name = clean(row.get("name"))
    province = clean(row.get("province"))
    area = clean(row.get("area"))

    notes = [
        "Ảnh phải khớp đúng địa điểm theo id và name.",
        "Không lấy ảnh chung chung của tỉnh/khu vực.",
        "Không lấy ảnh địa điểm cùng tên ở nơi khác.",
        "Không tự chế URL ảnh.",
        "Không dùng Google/Bing search URL làm image_url.",
        "image_url phải là URL ảnh trực tiếp mở ra ảnh.",
    ]

    if name and province:
        notes.append(f"Ưu tiên đúng {name} tại {province}.")

    if area:
        notes.append(f"Nếu có địa điểm trùng tên, ưu tiên khu vực {area}.")

    return " ".join(notes)


def fetch_rows(args):
    conn = connect(args)
    cur = conn.cursor()

    dest_cols = get_columns(cur, "destinations")

    if "rag_place_id" not in dest_cols:
        raise RuntimeError("destinations table must have rag_place_id column")

    select_parts = [
        safe_select_expr("d", dest_cols, "rag_place_id", "id"),
        safe_select_expr("d", dest_cols, "name"),
        safe_select_expr("d", dest_cols, "province"),
        safe_select_expr("d", dest_cols, "area"),
        safe_select_expr("d", dest_cols, "address"),
        safe_select_expr("d", dest_cols, "short_description"),
        safe_select_expr("d", dest_cols, "category"),
        safe_select_expr("d", dest_cols, "category_main"),
        safe_select_expr("d", dest_cols, "category_sub"),
        safe_select_expr("d", dest_cols, "source_url"),
    ]

    where = [
        "d.rag_place_id IS NOT NULL",
        "d.rag_place_id <> ''",
    ]
    params = []

    if args.province:
        if "province" not in dest_cols:
            raise RuntimeError("Cannot filter by province because destinations.province does not exist")
        where.append("d.province = %s")
        params.append(args.province)

    if args.only_missing_images:
        if "images_json" in dest_cols:
            where.append("(d.images_json IS NULL OR d.images_json = '' OR d.images_json = '[]')")
        else:
            print("[WARN] images_json column not found, ignoring --only-missing-images")

    where_sql = " AND ".join(where)

    if "province" in dest_cols:
        order_sql = "d.province, d.rag_place_id"
    else:
        order_sql = "d.rag_place_id"

    sql = f"""
        SELECT
            {", ".join(select_parts)}
        FROM destinations d
        WHERE {where_sql}
        ORDER BY {order_sql}
    """

    cur.execute(sql, params)
    columns = [desc[0] for desc in cur.description]
    rows = [dict(zip(columns, row)) for row in cur.fetchall()]

    cur.close()
    conn.close()

    return rows


def normalize_row(row):
    category = clean(row.get("category"))

    category_main = clean(row.get("category_main"))
    category_sub = clean(row.get("category_sub"))

    if not category:
        category = " / ".join([x for x in [category_main, category_sub] if x])

    q1, q2, q3 = build_queries({
        **row,
        "category": category,
    })

    return {
        "id": clean(row.get("id")),
        "name": clean(row.get("name")),
        "province": clean(row.get("province")),
        "area": clean(row.get("area")),
        "short_description": clean(row.get("short_description")),
        "category": category,
        "source_url": clean(row.get("source_url")),
        "aliases": build_aliases(row),
        "image_query_1": q1,
        "image_query_2": q2,
        "image_query_3": q3,
        "avoid_note": build_avoid_note(row),
    }


def export_batches(args):
    rows = fetch_rows(args)

    out_dir = ROOT_DIR / "data" / "image_prompt_batches_clean"
    out_dir.mkdir(parents=True, exist_ok=True)

    batch_size = max(1, args.batch_size)
    total_batches = math.ceil(len(rows) / batch_size)

    for batch_index in range(total_batches):
        start = batch_index * batch_size
        end = start + batch_size
        batch_rows = rows[start:end]

        batch_no = batch_index + 1
        out_path = out_dir / f"image_prompt_batch_{batch_no:03d}.csv"

        with out_path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=OUTPUT_HEADER)
            writer.writeheader()

            for row in batch_rows:
                writer.writerow(normalize_row(row))

        print(f"Created: {out_path} ({len(batch_rows)} rows)")

    print("")
    print("Export finished.")
    print(f"Total places : {len(rows)}")
    print(f"Batch size   : {batch_size}")
    print(f"Total batches: {total_batches}")
    print(f"Output dir   : {out_dir}")


def parse_args():
    parser = argparse.ArgumentParser(description="Export clean image prompt batches.")

    parser.add_argument("--province", default="", help="Filter by province, e.g. 'An Giang'")
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--only-missing-images", action="store_true")

    parser.add_argument("--db-host", default=os.getenv("DB_HOST", "127.0.0.1"))
    parser.add_argument("--db-port", type=int, default=int(os.getenv("DB_PORT", "3306")))
    parser.add_argument("--db-user", default=os.getenv("DB_USER", "root"))
    parser.add_argument("--db-password", default=os.getenv("DB_PASSWORD", ""))
    parser.add_argument("--db-name", default=os.getenv("DB_NAME", "unudata"))

    return parser.parse_args()


if __name__ == "__main__":
    export_batches(parse_args())
