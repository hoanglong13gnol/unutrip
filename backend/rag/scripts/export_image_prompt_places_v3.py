# -*- coding: utf-8 -*-
"""
Export enriched image-search batches for AI.

Output:
  data/image_prompt_batches_v3/image_prompt_batch_001.csv
  data/image_prompt_batches_v3/image_prompt_batch_002.csv
  ...

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


def build_aliases(row):
    name = clean(row.get("name"))
    province = clean(row.get("province"))
    area = clean(row.get("area"))
    city = clean(row.get("city"))

    aliases = [name]

    if area and area not in name:
        aliases.append(f"{name} {area}")

    if city and city not in name:
        aliases.append(f"{name} {city}")

    if province and province not in name:
        aliases.append(f"{name} {province}")

    # dedupe, keep order
    result = []
    seen = set()
    for item in aliases:
        key = item.lower()
        if item and key not in seen:
            seen.add(key)
            result.append(item)

    return " | ".join(result)


def build_search_context(row):
    parts = []

    name = clean(row.get("name"))
    province = clean(row.get("province"))
    city = clean(row.get("city"))
    area = clean(row.get("area"))
    address = clean(row.get("address"))
    category_main = clean(row.get("category_main"))
    category_sub = clean(row.get("category_sub"))
    short_description = clean(row.get("short_description"))
    source_url = clean(row.get("source_url"))
    source = clean(row.get("source"))

    if name:
        parts.append(f"Tên địa điểm: {name}")
    if area:
        parts.append(f"Khu vực/huyện/xã: {area}")
    if city:
        parts.append(f"Thành phố/quận/huyện: {city}")
    if province:
        parts.append(f"Tỉnh/thành: {province}")
    if address:
        parts.append(f"Địa chỉ: {address}")
    if category_main or category_sub:
        parts.append(f"Loại địa điểm: {category_main} / {category_sub}")
    if short_description:
        parts.append(f"Mô tả ngắn: {short_description}")
    if source_url:
        parts.append(f"Nguồn gốc trong dataset: {source_url}")
    if source:
        parts.append(f"Tên nguồn gốc: {source}")

    return "; ".join(parts)


def build_queries(row):
    name = clean(row.get("name"))
    province = clean(row.get("province"))
    city = clean(row.get("city"))
    area = clean(row.get("area"))
    category_main = clean(row.get("category_main"))

    place_bits = [name]
    if area:
        place_bits.append(area)
    if city and city != area:
        place_bits.append(city)
    if province:
        place_bits.append(province)

    full_place = " ".join([x for x in place_bits if x])

    q1 = f'{full_place} ảnh địa điểm du lịch'
    q2 = f'{full_place} hình ảnh'
    q3 = f'{full_place} jpg'
    q4 = f'{full_place} site:vietnamtourism.gov.vn OR site:vietnam.travel'
    q5 = f'{full_place} site:baoangiang.com.vn OR site:vnexpress.net OR site:mia.vn'

    if category_main:
        q2 = f'{full_place} {category_main} ảnh'

    return q1, q2, q3, q4, q5


def build_avoid_note(row):
    name = clean(row.get("name"))
    province = clean(row.get("province"))
    area = clean(row.get("area"))

    notes = [
        "Không lấy ảnh Google/Bing search làm image_url.",
        "Không lấy ảnh chung chung của tỉnh nếu không khớp đúng địa điểm.",
        "Không tự chế URL ảnh.",
        "Chỉ dùng URL ảnh trực tiếp mở ra ảnh."
    ]

    if province:
        notes.append(f"Ảnh phải liên quan đúng {name} ở {province}.")
    if area:
        notes.append(f"Nếu có địa điểm cùng tên, ưu tiên khu vực {area}.")

    return " ".join(notes)


def fetch_rows(args):
    conn = connect(args)
    cur = conn.cursor(dictionary=True)

    where = ["d.rag_place_id IS NOT NULL", "d.rag_place_id <> ''"]
    params = []

    if args.province:
        where.append("d.province = %s")
        params.append(args.province)

    if args.only_missing_images:
        where.append("(d.images_json IS NULL OR d.images_json = '' OR d.images_json = '[]')")

    where_sql = " AND ".join(where)

    sql = f"""
        SELECT
            d.id,
            d.rag_place_id,
            d.name,
            d.province,
            d.city,
            d.area,
            d.address,
            d.category,
            d.category_main,
            d.category_sub,
            d.short_description,
            d.rating,
            d.recommended_use,
            d.images_json,
            d.source_url,
            d.source,
            d.destination_group
        FROM destinations d
        WHERE {where_sql}
        ORDER BY d.province, d.rag_place_id
    """

    cur.execute(sql, params)
    rows = cur.fetchall()

    cur.close()
    conn.close()

    return rows


def export_batches(args):
    rows = fetch_rows(args)

    out_dir = ROOT_DIR / "data" / "image_prompt_batches_v3"
    out_dir.mkdir(parents=True, exist_ok=True)

    batch_size = max(1, args.batch_size)
    total_batches = math.ceil(len(rows) / batch_size)

    header = [
        "rag_place_id",
        "name",
        "province",
        "city",
        "area",
        "address",
        "category",
        "category_main",
        "category_sub",
        "short_description",
        "rating",
        "recommended_use",
        "current_images_json",
        "source_url",
        "source",
        "destination_group",
        "aliases",
        "search_context",
        "image_query_1",
        "image_query_2",
        "image_query_3",
        "official_source_query",
        "media_source_query",
        "avoid_note",
        "expected_output",
    ]

    for batch_index in range(total_batches):
        start = batch_index * batch_size
        end = start + batch_size
        batch_rows = rows[start:end]

        batch_no = batch_index + 1
        out_path = out_dir / f"image_prompt_batch_{batch_no:03d}.csv"

        with out_path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=header)
            writer.writeheader()

            for row in batch_rows:
                q1, q2, q3, q4, q5 = build_queries(row)

                writer.writerow({
                    "rag_place_id": clean(row.get("rag_place_id")),
                    "name": clean(row.get("name")),
                    "province": clean(row.get("province")),
                    "city": clean(row.get("city")),
                    "area": clean(row.get("area")),
                    "address": clean(row.get("address")),
                    "category": clean(row.get("category")),
                    "category_main": clean(row.get("category_main")),
                    "category_sub": clean(row.get("category_sub")),
                    "short_description": clean(row.get("short_description")),
                    "rating": clean(row.get("rating")),
                    "recommended_use": clean(row.get("recommended_use")),
                    "current_images_json": clean(row.get("images_json")),
                    "source_url": clean(row.get("source_url")),
                    "source": clean(row.get("source")),
                    "destination_group": clean(row.get("destination_group")),
                    "aliases": build_aliases(row),
                    "search_context": build_search_context(row),
                    "image_query_1": q1,
                    "image_query_2": q2,
                    "image_query_3": q3,
                    "official_source_query": q4,
                    "media_source_query": q5,
                    "avoid_note": build_avoid_note(row),
                    "expected_output": "Tìm 3-5 image_url trực tiếp cho địa điểm này; ưu tiên URL .jpg/.jpeg/.png/.webp/CDN ảnh mở trực tiếp; source_page_url là trang chứa ảnh.",
                })

        print(f"Created: {out_path} ({len(batch_rows)} rows)")

    print("")
    print("Export finished.")
    print(f"Total places : {len(rows)}")
    print(f"Batch size   : {batch_size}")
    print(f"Total batches: {total_batches}")
    print(f"Output dir   : {out_dir}")


def parse_args():
    parser = argparse.ArgumentParser(description="Export enriched image prompt batches.")

    parser.add_argument("--province", default="", help="Filter by province, e.g. 'An Giang'")
    parser.add_argument("--batch-size", type=int, default=20)
    parser.add_argument("--only-missing-images", action="store_true")

    parser.add_argument("--db-host", default=os.getenv("DB_HOST", "127.0.0.1"))
    parser.add_argument("--db-port", type=int, default=int(os.getenv("DB_PORT", "3306")))
    parser.add_argument("--db-user", default=os.getenv("DB_USER", "root"))
    parser.add_argument("--db-password", default=os.getenv("DB_PASSWORD", ""))
    parser.add_argument("--db-name", default=os.getenv("DB_NAME", "unudata"))

    return parser.parse_args()


if __name__ == "__main__":
    export_batches(parse_args())


