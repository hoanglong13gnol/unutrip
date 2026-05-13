# -*- coding: utf-8 -*-
"""
Export clean destination list for AI-assisted real image sourcing.

Output:
  data/image_prompt_places.csv
  data/image_prompt_batches/image_prompt_batch_001.csv ...

Purpose:
  Use these CSV files to ask AI / yourself to find real image URLs later.
  This script DOES NOT import images and DOES NOT modify database.

Source tables:
  destinations
  rag_places
"""

import argparse
import csv
import os
from pathlib import Path

import mysql.connector


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT_DIR / "data" / "image_prompt_places.csv"
DEFAULT_BATCH_DIR = ROOT_DIR / "data" / "image_prompt_batches"


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


def clean_text(value):
    if value is None:
        return ""
    return str(value).replace("\r", " ").replace("\n", " ").strip()


def build_search_queries(row):
    name = clean_text(row.get("name"))
    province = clean_text(row.get("province"))
    area = clean_text(row.get("area"))
    category_sub = clean_text(row.get("category_sub"))

    base = " ".join(x for x in [name, area, province] if x)
    if not base:
        base = name

    return {
        "official_search_query": f"{base} ảnh chính thức du lịch",
        "image_search_query": f"{base} {category_sub} ảnh địa điểm du lịch",
        "wikimedia_search_query": f"{base} Wikimedia Commons",
        "source_page_search_query": f"{base} site:vietnam.travel OR site:vietnamtourism.gov.vn OR site:*.gov.vn",
    }


def fetch_rows(args):
    conn = connect(args)
    cur = conn.cursor(dictionary=True)

    where_clauses = [
        "d.is_active = 1",
        "d.rag_place_id IS NOT NULL",
    ]
    params = []

    if args.missing_images_only:
        where_clauses.append("(d.images_json IS NULL OR d.images_json = '' OR d.images_json = '[]')")

    if args.province:
        where_clauses.append("d.province = %s")
        params.append(args.province)

    if args.category_main:
        where_clauses.append("d.category_main = %s")
        params.append(args.category_main)

    where_sql = " AND ".join(where_clauses)

    limit_sql = ""
    if args.limit > 0:
        limit_sql = "LIMIT %s"
        params.append(args.limit)

    sql = f"""
        SELECT
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
          d.images_json,
          d.rating,
          r.source_url,
          r.source,
          r.destination_group,
          r.quality_score,
          r.recommended_use_norm,
          r.requires_realtime_check
        FROM destinations d
        LEFT JOIN rag_places r ON r.place_id = d.rag_place_id
        WHERE {where_sql}
        ORDER BY
          d.province ASC,
          d.category_main ASC,
          d.rag_place_id ASC
        {limit_sql}
    """

    cur.execute(sql, params)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def write_csv(rows, output_path):
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fields = [
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
        "quality_score",
        "recommended_use",
        "requires_realtime_check",
        "current_images_json",
        "source_url",
        "source",
        "destination_group",
        "official_search_query",
        "image_search_query",
        "wikimedia_search_query",
        "source_page_search_query",
        "notes_for_human_check",
    ]

    with output_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()

        for row in rows:
            queries = build_search_queries(row)
            writer.writerow({
                "rag_place_id": clean_text(row.get("rag_place_id")),
                "name": clean_text(row.get("name")),
                "province": clean_text(row.get("province")),
                "city": clean_text(row.get("city")),
                "area": clean_text(row.get("area")),
                "address": clean_text(row.get("address")),
                "category": clean_text(row.get("category")),
                "category_main": clean_text(row.get("category_main")),
                "category_sub": clean_text(row.get("category_sub")),
                "short_description": clean_text(row.get("short_description")),
                "rating": clean_text(row.get("rating")),
                "quality_score": clean_text(row.get("quality_score")),
                "recommended_use": clean_text(row.get("recommended_use_norm")),
                "requires_realtime_check": clean_text(row.get("requires_realtime_check")),
                "current_images_json": clean_text(row.get("images_json")),
                "source_url": clean_text(row.get("source_url")),
                "source": clean_text(row.get("source")),
                "destination_group": clean_text(row.get("destination_group")),
                "official_search_query": queries["official_search_query"],
                "image_search_query": queries["image_search_query"],
                "wikimedia_search_query": queries["wikimedia_search_query"],
                "source_page_search_query": queries["source_page_search_query"],
                "notes_for_human_check": "Chỉ dùng image_url trực tiếp .jpg/.png/.webp; không dùng trang HTML, ảnh random, placeholder; phải ghi nguồn/credit.",
            })


def write_batches(rows, batch_dir, batch_size):
    batch_dir.mkdir(parents=True, exist_ok=True)
    outputs = []

    for i in range(0, len(rows), batch_size):
        batch_no = i // batch_size + 1
        batch_rows = rows[i:i + batch_size]
        path = batch_dir / f"image_prompt_batch_{batch_no:03d}.csv"
        write_csv(batch_rows, path)
        outputs.append(path)

    return outputs


def parse_args():
    parser = argparse.ArgumentParser(description="Export clean destinations for AI image sourcing prompts.")

    parser.add_argument("--db-host", default=os.getenv("DB_HOST", "127.0.0.1"))
    parser.add_argument("--db-port", type=int, default=int(os.getenv("DB_PORT", "3306")))
    parser.add_argument("--db-user", default=os.getenv("DB_USER", "root"))
    parser.add_argument("--db-password", default=os.getenv("DB_PASSWORD", ""))
    parser.add_argument("--db-name", default=os.getenv("DB_NAME", "unudata"))

    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--batch-dir", default=str(DEFAULT_BATCH_DIR))
    parser.add_argument("--batch-size", type=int, default=50)

    parser.add_argument("--province", default="", help="Optional province filter, e.g. Khánh Hòa")
    parser.add_argument("--category-main", default="", help="Optional category_main filter, e.g. Thiên nhiên")
    parser.add_argument("--limit", type=int, default=0, help="0 means no limit")
    parser.add_argument("--missing-images-only", action="store_true", help="Export only places with images_json empty")

    return parser.parse_args()


def main():
    args = parse_args()

    rows = fetch_rows(args)
    output_path = Path(args.output)
    batch_dir = Path(args.batch_dir)

    write_csv(rows, output_path)
    batch_paths = write_batches(rows, batch_dir, args.batch_size)

    print("[DONE] Exported places for AI image sourcing")
    print(f"Rows      : {len(rows)}")
    print(f"Main CSV  : {output_path}")
    print(f"Batch dir : {batch_dir}")
    print(f"Batches   : {len(batch_paths)}")
    if batch_paths:
        print(f"First     : {batch_paths[0]}")
        print(f"Last      : {batch_paths[-1]}")


if __name__ == "__main__":
    main()
