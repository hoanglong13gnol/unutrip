#!/usr/bin/env python
# -*- coding: utf-8 -*-

r"""
Export places from MySQL for UnuTrip / SmartTravel image pipeline.

Purpose:
- Read places from MySQL database `unudata`.
- Export a clean CSV input for image collection/search pipeline.
- Prefer places with missing/no images, but can export all places.
- Safely checks existing columns before querying.
- Does NOT update database.

Default DB:
host=127.0.0.1
port=3306
user=root
password=<empty>
database=unudata

Output columns:
rag_place_id,name,province,area,short_description,category,source_url,aliases,image_query_1,image_query_2,image_query_3,avoid_note,existing_image_count,images_json

Examples:
python .\scripts\export_places_for_image_pipeline.py

Export first 100 places with missing images:
python .\scripts\export_places_for_image_pipeline.py ^
  --limit 100 ^
  --missing-only

Export all places:
python .\scripts\export_places_for_image_pipeline.py ^
  --all

Output default:
data\image_pipeline\input\places_for_image_pipeline.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

try:
    import mysql.connector
except ImportError as exc:
    raise SystemExit(
        "Missing dependency: mysql-connector-python\n"
        "Install it with:\n"
        "  pip install mysql-connector-python"
    ) from exc


OUTPUT_FIELDS = [
    "rag_place_id",
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
    "existing_image_count",
    "images_json",
]

DESTINATION_PREFERRED_FIELDS = [
    "id",
    "rag_place_id",
    "name",
    "province",
    "city",
    "area",
    "address",
    "short_description",
    "description",
    "category",
    "category_main",
    "category_sub",
    "source_url",
    "source",
    "images_json",
]

RAG_PLACE_PREFERRED_FIELDS = [
    "id",
    "destination_id",
    "rag_place_id",
    "name",
    "province",
    "city",
    "area",
    "address",
    "short_description",
    "description",
    "category",
    "category_main",
    "category_sub",
    "source_url",
    "source",
    "raw_json",
]


class DbConfig:
    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        database: str,
    ) -> None:
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_csv(path: Path, fieldnames: List[str], rows: Iterable[Dict[str, str]]) -> int:
    ensure_parent_dir(path)
    count = 0

    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
            count += 1

    return count


def connect_db(config: DbConfig):
    return mysql.connector.connect(
        host=config.host,
        port=config.port,
        user=config.user,
        password=config.password,
        database=config.database,
        charset="utf8mb4",
        use_unicode=True,
    )


def get_table_columns(conn, table_name: str) -> Set[str]:
    cursor = conn.cursor()
    try:
        cursor.execute(f"DESCRIBE `{table_name}`")
        return {str(row[0]) for row in cursor.fetchall()}
    finally:
        cursor.close()


def table_exists(conn, table_name: str) -> bool:
    cursor = conn.cursor()
    try:
        cursor.execute("SHOW TABLES LIKE %s", (table_name,))
        return cursor.fetchone() is not None
    finally:
        cursor.close()


def select_existing_fields(alias: str, preferred_fields: Sequence[str], existing_columns: Set[str]) -> List[str]:
    fields = []
    for field in preferred_fields:
        if field in existing_columns:
            fields.append(f"{alias}.`{field}` AS `{alias}_{field}`")
    return fields


def first_value(row: Dict[str, Any], keys: Sequence[str]) -> str:
    for key in keys:
        value = clean_text(row.get(key, ""))
        if value:
            return value
    return ""


def parse_json_list_count(value: str) -> int:
    value = clean_text(value)
    if not value:
        return 0

    try:
        data = json.loads(value)
    except Exception:
        return 0

    if isinstance(data, list):
        return len([item for item in data if item])

    if isinstance(data, str):
        return 1 if data.strip() else 0

    return 0


def slugish_alias(name: str) -> str:
    # Keep this simple and safe. Search APIs handle Vietnamese well, so aliases are supplementary.
    text = clean_text(name)
    text = re.sub(r"[\"'“”‘’]", "", text)
    return text


def build_category(row: Dict[str, Any]) -> str:
    parts = []
    for key in (
        "d_category",
        "d_category_main",
        "d_category_sub",
        "r_category",
        "r_category_main",
        "r_category_sub",
    ):
        value = clean_text(row.get(key, ""))
        if value and value not in parts:
            parts.append(value)
    return " / ".join(parts)


def build_source_url(row: Dict[str, Any]) -> str:
    return first_value(
        row,
        [
            "d_source_url",
            "r_source_url",
            "d_source",
            "r_source",
        ],
    )


def build_short_description(row: Dict[str, Any]) -> str:
    return first_value(
        row,
        [
            "d_short_description",
            "r_short_description",
            "d_description",
            "r_description",
        ],
    )


def build_area(row: Dict[str, Any]) -> str:
    return first_value(
        [row][0],
        [
            "d_area",
            "r_area",
            "d_city",
            "r_city",
            "d_address",
            "r_address",
        ],
    )


def build_queries(name: str, area: str, province: str, category: str) -> Tuple[str, str, str]:
    name = clean_text(name)
    area = clean_text(area)
    province = clean_text(province)
    category = clean_text(category)

    location_bits = " ".join(bit for bit in [area, province] if bit)

    query_1 = normalize_space(f"{name} {location_bits} ảnh")
    query_2 = normalize_space(f"{name} {location_bits} hình ảnh")

    if category:
        query_3 = normalize_space(f"{name} {province} {category} jpg")
    else:
        query_3 = normalize_space(f"{name} {province} jpg jpeg png webp")

    return query_1, query_2, query_3


def build_avoid_note(name: str, province: str, area: str) -> str:
    pieces = [
        "Không dùng Google/Bing search URL làm image_url.",
        "Không dùng ảnh logo, icon, bản đồ, ảnh quá nhỏ hoặc ảnh HTML page.",
        "Ảnh phải khớp đúng địa điểm, không chỉ khớp tỉnh/thành.",
    ]

    if province:
        pieces.append(f"Ưu tiên ảnh có ngữ cảnh {province}.")
    if area:
        pieces.append(f"Tránh nhầm với địa điểm khác cùng tên ngoài khu vực {area}.")

    return " ".join(pieces)


def fetch_existing_image_counts(conn, destination_ids: List[int]) -> Dict[int, int]:
    if not destination_ids:
        return {}

    if not table_exists(conn, "destination_images"):
        return {}

    columns = get_table_columns(conn, "destination_images")
    if "destination_id" not in columns:
        return {}

    counts: Dict[int, int] = {}
    cursor = conn.cursor(dictionary=True)

    try:
        chunk_size = 500
        for i in range(0, len(destination_ids), chunk_size):
            chunk = destination_ids[i : i + chunk_size]
            placeholders = ",".join(["%s"] * len(chunk))
            query = (
                "SELECT destination_id, COUNT(*) AS image_count "
                "FROM destination_images "
                f"WHERE destination_id IN ({placeholders}) "
                "GROUP BY destination_id"
            )
            cursor.execute(query, tuple(chunk))
            for row in cursor.fetchall():
                try:
                    counts[int(row["destination_id"])] = int(row["image_count"] or 0)
                except Exception:
                    continue
    finally:
        cursor.close()

    return counts


def build_query(conn, limit: int, offset: int) -> Tuple[str, List[Any], List[str]]:
    d_cols = get_table_columns(conn, "destinations")
    r_cols = get_table_columns(conn, "rag_places") if table_exists(conn, "rag_places") else set()

    select_fields = select_existing_fields("d", DESTINATION_PREFERRED_FIELDS, d_cols)
    joins = ""

    if r_cols:
        select_fields.extend(select_existing_fields("r", RAG_PLACE_PREFERRED_FIELDS, r_cols))

        if "destination_id" in r_cols and "id" in d_cols:
            joins = "LEFT JOIN rag_places r ON r.destination_id = d.id"
        elif "rag_place_id" in r_cols and "rag_place_id" in d_cols:
            joins = "LEFT JOIN rag_places r ON r.rag_place_id = d.rag_place_id"
        else:
            joins = ""

    if not select_fields:
        raise RuntimeError("No usable columns found in destinations/rag_places")

    query = f"SELECT {', '.join(select_fields)} FROM destinations d {joins} ORDER BY d.id"
    params: List[Any] = []

    if limit > 0:
        query += " LIMIT %s OFFSET %s"
        params.extend([limit, offset])

    return query, params, select_fields


def export_rows(
    conn,
    limit: int,
    offset: int,
    missing_only: bool,
    target_images: int,
) -> List[Dict[str, str]]:
    query, params, _ = build_query(conn, limit=limit, offset=offset)

    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(query, tuple(params))
        raw_rows = cursor.fetchall()
    finally:
        cursor.close()

    destination_ids: List[int] = []
    for row in raw_rows:
        try:
            destination_id = int(row.get("d_id") or 0)
            if destination_id:
                destination_ids.append(destination_id)
        except Exception:
            pass

    db_image_counts = fetch_existing_image_counts(conn, destination_ids)

    output_rows: List[Dict[str, str]] = []

    for row in raw_rows:
        destination_id = 0
        try:
            destination_id = int(row.get("d_id") or 0)
        except Exception:
            destination_id = 0

        images_json = clean_text(row.get("d_images_json", ""))
        images_json_count = parse_json_list_count(images_json)
        destination_image_count = db_image_counts.get(destination_id, 0)
        existing_image_count = max(images_json_count, destination_image_count)

        if missing_only and existing_image_count >= target_images:
            continue

        rag_place_id = first_value(row, ["d_rag_place_id", "r_rag_place_id", "r_id"])
        name = first_value(row, ["d_name", "r_name"])
        province = first_value(row, ["d_province", "r_province", "d_city", "r_city"])
        area = build_area(row)
        short_description = build_short_description(row)
        category = build_category(row)
        source_url = build_source_url(row)
        aliases = slugish_alias(name)

        query_1, query_2, query_3 = build_queries(
            name=name,
            area=area,
            province=province,
            category=category,
        )

        output_rows.append(
            {
                "rag_place_id": rag_place_id,
                "name": name,
                "province": province,
                "area": area,
                "short_description": short_description,
                "category": category,
                "source_url": source_url,
                "aliases": aliases,
                "image_query_1": query_1,
                "image_query_2": query_2,
                "image_query_3": query_3,
                "avoid_note": build_avoid_note(name, province, area),
                "existing_image_count": str(existing_image_count),
                "images_json": images_json,
            }
        )

    return output_rows


def default_output_path(project_root: Path) -> Path:
    return project_root / "data" / "image_pipeline" / "input" / "places_for_image_pipeline.csv"


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export places from MySQL to image pipeline input CSV."
    )

    parser.add_argument("--db-host", default="127.0.0.1", help="MySQL host. Default: 127.0.0.1")
    parser.add_argument("--db-port", type=int, default=3306, help="MySQL port. Default: 3306")
    parser.add_argument("--db-user", default="root", help="MySQL user. Default: root")
    parser.add_argument("--db-password", default="", help="MySQL password. Default: empty")
    parser.add_argument("--db-name", default="unudata", help="MySQL database name. Default: unudata")

    parser.add_argument(
        "--output",
        default="",
        help="Output CSV path. Default: data/image_pipeline/input/places_for_image_pipeline.csv",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Max rows to read from destinations. Use --all for no limit. Default: 100",
    )

    parser.add_argument(
        "--offset",
        type=int,
        default=0,
        help="SQL offset. Default: 0",
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="Export all rows instead of using --limit.",
    )

    parser.add_argument(
        "--missing-only",
        action="store_true",
        help="Only export places with fewer than --target-images existing images.",
    )

    parser.add_argument(
        "--target-images",
        type=int,
        default=1,
        help="Existing image threshold for --missing-only. Default: 1",
    )

    parser.add_argument(
        "--project-root",
        default=".",
        help="Project root. Default: current directory.",
    )

    return parser.parse_args(argv)


def resolve_path(path_text: str, project_root: Path) -> Path:
    path = Path(path_text)
    if not path.is_absolute():
        path = (project_root / path).resolve()
    return path


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)

    project_root = Path(args.project_root).resolve()
    output_path = resolve_path(args.output, project_root) if args.output else default_output_path(project_root)

    config = DbConfig(
        host=args.db_host,
        port=args.db_port,
        user=args.db_user,
        password=args.db_password,
        database=args.db_name,
    )

    limit = 0 if args.all else args.limit

    conn = connect_db(config)
    try:
        if not table_exists(conn, "destinations"):
            raise RuntimeError("Table not found: destinations")

        rows = export_rows(
            conn=conn,
            limit=limit,
            offset=args.offset,
            missing_only=args.missing_only,
            target_images=args.target_images,
        )
    finally:
        conn.close()

    written = write_csv(output_path, OUTPUT_FIELDS, rows)

    print(f"DB: {args.db_host}:{args.db_port}/{args.db_name}")
    print(f"Mode: {'all rows' if args.all else f'limit={args.limit} offset={args.offset}'}")
    print(f"Missing only: {args.missing_only} | target_images={args.target_images}")
    print(f"Rows exported: {written}")
    print(f"Output file: {output_path}")

    if written == 0:
        print("No rows exported. If you used --missing-only, existing images may already meet target or the limit window had no missing rows.")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print()
        print("Cancelled by user.", file=sys.stderr)
        raise SystemExit(130)
