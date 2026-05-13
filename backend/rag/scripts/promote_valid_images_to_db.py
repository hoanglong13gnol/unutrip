#!/usr/bin/env python
# -*- coding: utf-8 -*-

r"""
Promote approved image candidates into MySQL for UnuTrip / SmartTravel.

This version is customized for the schema in unudata.sql:

destinations:
- id
- rag_place_id
- name
- images_json
- image_source
- image_credit
- updated_at

destination_images:
- id
- destination_id
- rag_place_id
- image_url
- source
- credit
- license_note
- is_primary
- status
- created_at
- updated_at

No image_order/source_page_url columns exist in destination_images, so this script does not insert them there.
If --update-images-json is used, source_page_url/order/is_primary are stored inside destinations.images_json.

Dry-run first:
python .\scripts\promote_valid_images_to_db.py ^
  --input .\data\image_pipeline\final\source_pages_from_search_raw_approved_auto.csv

Apply insert only:
python .\scripts\promote_valid_images_to_db.py ^
  --input .\data\image_pipeline\final\source_pages_from_search_raw_approved_auto.csv ^
  --apply

Apply insert and update destinations.images_json:
python .\scripts\promote_valid_images_to_db.py ^
  --input .\data\image_pipeline\final\source_pages_from_search_raw_approved_auto.csv ^
  --apply ^
  --update-images-json

Apply and replace existing images for affected destinations:
python .\scripts\promote_valid_images_to_db.py ^
  --input .\data\image_pipeline\final\source_pages_from_search_raw_approved_auto.csv ^
  --apply ^
  --replace-existing ^
  --update-images-json
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
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


DESTINATION_BACKUP_FIELDS = [
    "id",
    "rag_place_id",
    "name",
    "images_json",
    "image_source",
    "image_credit",
    "updated_at",
]

DESTINATION_IMAGE_BACKUP_FIELDS = [
    "id",
    "destination_id",
    "rag_place_id",
    "image_url",
    "source",
    "credit",
    "license_note",
    "is_primary",
    "status",
    "created_at",
    "updated_at",
]

DESTINATION_IMAGE_INSERT_FIELDS = [
    "destination_id",
    "rag_place_id",
    "image_url",
    "source",
    "credit",
    "license_note",
    "is_primary",
    "status",
]

PROMOTE_LOG_FIELDS = [
    "rag_place_id",
    "destination_id",
    "place_name",
    "image_url",
    "source_page_url",
    "source",
    "final_rank",
    "is_primary",
    "match_score",
    "action",
    "reason",
]


class DbConfig:
    def __init__(self, host: str, port: int, user: str, password: str, database: str) -> None:
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def now_utc_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def parse_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(clean_text(value)))
    except Exception:
        return default


def truthy(value: Any) -> bool:
    text = clean_text(value).lower()
    return text in {"1", "true", "yes", "y", "primary"}


def read_csv_rows(path: Path) -> Tuple[List[str], List[Dict[str, str]]]:
    if not path.exists():
        raise FileNotFoundError(f"Input CSV not found: {path}")

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError(f"Input CSV has no header: {path}")
        return list(reader.fieldnames), list(reader)


def ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_csv(path: Path, fieldnames: List[str], rows: Iterable[Dict[str, Any]]) -> int:
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


def table_exists(conn, table_name: str) -> bool:
    cursor = conn.cursor()
    try:
        cursor.execute("SHOW TABLES LIKE %s", (table_name,))
        return cursor.fetchone() is not None
    finally:
        cursor.close()


def get_table_columns(conn, table_name: str) -> Set[str]:
    cursor = conn.cursor()
    try:
        cursor.execute(f"DESCRIBE `{table_name}`")
        return {str(row[0]) for row in cursor.fetchall()}
    finally:
        cursor.close()


def require_columns(conn, table_name: str, required_columns: Sequence[str]) -> None:
    columns = get_table_columns(conn, table_name)
    missing = [col for col in required_columns if col not in columns]
    if missing:
        raise RuntimeError(f"Table {table_name} missing required columns: {', '.join(missing)}")


def quote_cols(cols: Sequence[str]) -> str:
    return ", ".join(f"`{col}`" for col in cols)


def get_first_existing(row: Dict[str, str], names: Sequence[str]) -> str:
    for name in names:
        value = clean_text(row.get(name, ""))
        if value:
            return value
    return ""


def get_rag_place_id(row: Dict[str, str]) -> str:
    return get_first_existing(row, ["rag_place_id", "place_id", "id"])


def get_place_name(row: Dict[str, str]) -> str:
    return get_first_existing(row, ["place_name", "name", "title"])


def get_image_url(row: Dict[str, str]) -> str:
    return get_first_existing(row, ["final_image_url", "image_url", "url"])


def get_source_page_url(row: Dict[str, str]) -> str:
    return get_first_existing(row, ["source_page_url", "source_url", "page_url"])


def get_rank(row: Dict[str, str]) -> int:
    return parse_int(row.get("final_rank", row.get("image_order", "999")), 999)


def selected_rows(rows: List[Dict[str, str]], min_score: int) -> List[Dict[str, str]]:
    selected: List[Dict[str, str]] = []
    seen = set()

    for row in rows:
        rag_place_id = get_rag_place_id(row)
        image_url = get_image_url(row)
        if not rag_place_id or not image_url:
            continue

        match_status = clean_text(row.get("match_status", ""))
        if match_status and match_status != "APPROVED_AUTO":
            continue

        if "selected_for_final" in row and not truthy(row.get("selected_for_final", "")):
            continue

        if parse_int(row.get("match_score", "0"), 0) < min_score:
            continue

        key = (rag_place_id, image_url.lower())
        if key in seen:
            continue
        seen.add(key)
        selected.append(row)

    selected.sort(
        key=lambda r: (
            get_rag_place_id(r),
            get_rank(r),
            -parse_int(r.get("match_score", "0"), 0),
            get_image_url(r),
        )
    )
    return selected


def fetch_destinations_by_rag_place_id(conn, rag_place_ids: List[str]) -> Dict[str, Dict[str, Any]]:
    if not rag_place_ids:
        return {}

    require_columns(conn, "destinations", ["id", "rag_place_id"])
    columns = get_table_columns(conn, "destinations")
    select_cols = [col for col in DESTINATION_BACKUP_FIELDS if col in columns]
    if "id" not in select_cols:
        select_cols.insert(0, "id")
    if "rag_place_id" not in select_cols:
        select_cols.insert(1, "rag_place_id")

    result: Dict[str, Dict[str, Any]] = {}
    cursor = conn.cursor(dictionary=True)

    try:
        chunk_size = 500
        for i in range(0, len(rag_place_ids), chunk_size):
            chunk = rag_place_ids[i : i + chunk_size]
            placeholders = ",".join(["%s"] * len(chunk))
            query = (
                f"SELECT {quote_cols(select_cols)} "
                f"FROM destinations "
                f"WHERE rag_place_id IN ({placeholders})"
            )
            cursor.execute(query, tuple(chunk))
            for row in cursor.fetchall():
                key = clean_text(row.get("rag_place_id"))
                if key:
                    result[key] = dict(row)
    finally:
        cursor.close()

    return result


def fetch_destination_images(conn, destination_ids: List[int]) -> List[Dict[str, Any]]:
    if not destination_ids or not table_exists(conn, "destination_images"):
        return []

    columns = get_table_columns(conn, "destination_images")
    select_cols = [col for col in DESTINATION_IMAGE_BACKUP_FIELDS if col in columns]
    if not select_cols:
        return []

    order_cols = [col for col in ["destination_id", "is_primary", "id"] if col in columns]
    order_sql = " ORDER BY " + quote_cols(order_cols) if order_cols else ""

    rows: List[Dict[str, Any]] = []
    cursor = conn.cursor(dictionary=True)

    try:
        chunk_size = 500
        for i in range(0, len(destination_ids), chunk_size):
            chunk = destination_ids[i : i + chunk_size]
            placeholders = ",".join(["%s"] * len(chunk))
            query = (
                f"SELECT {quote_cols(select_cols)} "
                f"FROM destination_images "
                f"WHERE destination_id IN ({placeholders})"
                f"{order_sql}"
            )
            cursor.execute(query, tuple(chunk))
            rows.extend(dict(row) for row in cursor.fetchall())
    finally:
        cursor.close()

    return rows


def existing_image_urls_by_destination(conn, destination_ids: List[int]) -> Dict[int, Set[str]]:
    result: Dict[int, Set[str]] = defaultdict(set)
    if not destination_ids or not table_exists(conn, "destination_images"):
        return result

    require_columns(conn, "destination_images", ["destination_id", "image_url"])

    cursor = conn.cursor(dictionary=True)
    try:
        chunk_size = 500
        for i in range(0, len(destination_ids), chunk_size):
            chunk = destination_ids[i : i + chunk_size]
            placeholders = ",".join(["%s"] * len(chunk))
            query = (
                f"SELECT destination_id, image_url "
                f"FROM destination_images "
                f"WHERE destination_id IN ({placeholders})"
            )
            cursor.execute(query, tuple(chunk))
            for row in cursor.fetchall():
                destination_id = parse_int(row.get("destination_id"), 0)
                image_url = clean_text(row.get("image_url", "")).lower()
                if destination_id and image_url:
                    result[destination_id].add(image_url)
    finally:
        cursor.close()

    return result


def backup_affected_data(conn, destination_map: Dict[str, Dict[str, Any]], backup_dir: Path, tag: str) -> Tuple[Path, Path, int, int]:
    ensure_parent_dir(backup_dir / "dummy.txt")

    destination_ids: List[int] = []
    destination_rows: List[Dict[str, Any]] = []

    destination_columns = get_table_columns(conn, "destinations")
    destination_backup_fields = [col for col in DESTINATION_BACKUP_FIELDS if col in destination_columns]

    for rag_place_id, destination in sorted(destination_map.items()):
        destination_id = parse_int(destination.get("id"), 0)
        if not destination_id:
            continue
        destination_ids.append(destination_id)
        destination_rows.append({field: destination.get(field, "") for field in destination_backup_fields})

    image_rows = fetch_destination_images(conn, destination_ids)
    image_columns = get_table_columns(conn, "destination_images") if table_exists(conn, "destination_images") else set()
    image_backup_fields = [col for col in DESTINATION_IMAGE_BACKUP_FIELDS if col in image_columns]
    if not image_backup_fields:
        image_backup_fields = DESTINATION_IMAGE_BACKUP_FIELDS

    dest_backup_path = backup_dir / f"backup_destinations_{tag}.csv"
    image_backup_path = backup_dir / f"backup_destination_images_{tag}.csv"

    dest_count = write_csv(dest_backup_path, destination_backup_fields, destination_rows)
    image_count = write_csv(image_backup_path, image_backup_fields, image_rows)

    return dest_backup_path, image_backup_path, dest_count, image_count


def delete_existing_images(conn, destination_ids: List[int]) -> int:
    if not destination_ids or not table_exists(conn, "destination_images"):
        return 0

    require_columns(conn, "destination_images", ["destination_id"])

    cursor = conn.cursor()
    try:
        placeholders = ",".join(["%s"] * len(destination_ids))
        cursor.execute(
            f"DELETE FROM destination_images WHERE destination_id IN ({placeholders})",
            tuple(destination_ids),
        )
        return int(cursor.rowcount or 0)
    finally:
        cursor.close()


def insert_destination_images(conn, rows: List[Dict[str, str]], destination_map: Dict[str, Dict[str, Any]], replace_existing: bool) -> Tuple[int, List[Dict[str, Any]]]:
    require_columns(conn, "destination_images", DESTINATION_IMAGE_INSERT_FIELDS)

    destination_ids = [parse_int(dest.get("id"), 0) for dest in destination_map.values() if parse_int(dest.get("id"), 0)]
    existing_urls = defaultdict(set) if replace_existing else existing_image_urls_by_destination(conn, destination_ids)

    values: List[Tuple[Any, ...]] = []
    log_rows: List[Dict[str, Any]] = []

    for row in rows:
        rag_place_id = get_rag_place_id(row)
        destination = destination_map.get(rag_place_id)
        image_url = get_image_url(row)

        if not destination:
            log_rows.append(build_log_row(row, "SKIP", "destination_not_found", ""))
            continue

        destination_id = parse_int(destination.get("id"), 0)
        if not destination_id:
            log_rows.append(build_log_row(row, "SKIP", "destination_id_missing", ""))
            continue

        if image_url.lower() in existing_urls[destination_id]:
            log_rows.append(build_log_row(row, "SKIP", "image_url_already_exists", str(destination_id)))
            continue

        rank = get_rank(row)
        is_primary = 1 if rank == 1 else 0

        values.append(
            (
                destination_id,
                rag_place_id,
                image_url,
                clean_text(row.get("source", "")),
                clean_text(row.get("credit", "")),
                clean_text(row.get("license_note", "")),
                is_primary,
                "active",
            )
        )
        existing_urls[destination_id].add(image_url.lower())
        log_rows.append(build_log_row(row, "INSERT", "ok", str(destination_id), is_primary=is_primary))

    if not values:
        return 0, log_rows

    cursor = conn.cursor()
    try:
        placeholders = ",".join(["%s"] * len(DESTINATION_IMAGE_INSERT_FIELDS))
        query = f"INSERT INTO destination_images ({quote_cols(DESTINATION_IMAGE_INSERT_FIELDS)}) VALUES ({placeholders})"
        cursor.executemany(query, values)
        return int(cursor.rowcount or 0), log_rows
    finally:
        cursor.close()


def build_images_json_by_destination(rows: List[Dict[str, str]], destination_map: Dict[str, Dict[str, Any]]) -> Dict[int, str]:
    grouped: Dict[int, List[Dict[str, str]]] = defaultdict(list)

    for row in rows:
        rag_place_id = get_rag_place_id(row)
        destination = destination_map.get(rag_place_id)
        if not destination:
            continue
        destination_id = parse_int(destination.get("id"), 0)
        if not destination_id:
            continue
        if not get_image_url(row):
            continue
        grouped[destination_id].append(row)

    result: Dict[int, str] = {}

    for destination_id, image_rows in grouped.items():
        image_rows.sort(key=lambda row: get_rank(row))
        data = []
        seen = set()

        for index, row in enumerate(image_rows, start=1):
            image_url = get_image_url(row)
            if image_url.lower() in seen:
                continue
            seen.add(image_url.lower())
            data.append(
                {
                    "url": image_url,
                    "source_page_url": get_source_page_url(row),
                    "source": clean_text(row.get("source", "")),
                    "credit": clean_text(row.get("credit", "")),
                    "license_note": clean_text(row.get("license_note", "")),
                    "order": index,
                    "is_primary": index == 1,
                    "match_score": parse_int(row.get("match_score", "0"), 0),
                }
            )

        result[destination_id] = json.dumps(data, ensure_ascii=False)

    return result


def update_destinations_images_json(conn, images_json_by_destination: Dict[int, str]) -> int:
    if not images_json_by_destination:
        return 0

    require_columns(conn, "destinations", ["id", "images_json"])

    cursor = conn.cursor()
    try:
        values = [(images_json, destination_id) for destination_id, images_json in images_json_by_destination.items()]
        cursor.executemany("UPDATE destinations SET images_json = %s WHERE id = %s", values)
        return int(cursor.rowcount or 0)
    finally:
        cursor.close()


def build_log_row(row: Dict[str, Any], action: str, reason: str, destination_id: str, is_primary: Optional[int] = None) -> Dict[str, Any]:
    return {
        "rag_place_id": get_rag_place_id(row),
        "destination_id": destination_id,
        "place_name": get_place_name(row),
        "image_url": get_image_url(row),
        "source_page_url": get_source_page_url(row),
        "source": clean_text(row.get("source", "")),
        "final_rank": str(get_rank(row)),
        "is_primary": is_primary if is_primary is not None else clean_text(row.get("is_primary", "")),
        "match_score": clean_text(row.get("match_score", "")),
        "action": action,
        "reason": reason,
    }


def default_paths(project_root: Path) -> Tuple[Path, Path]:
    tag = now_utc_compact()
    backup_dir = project_root / "data" / "image_pipeline" / "backup" / tag
    log_path = project_root / "data" / "image_pipeline" / "logs" / f"promote_images_{tag}.csv"
    return backup_dir, log_path


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Promote approved image CSV rows into MySQL for current unudata schema.")

    parser.add_argument("--input", required=True, help="Approved auto CSV from score_image_candidates.py.")
    parser.add_argument("--apply", action="store_true", help="Actually write to DB. Default is dry-run.")
    parser.add_argument("--replace-existing", action="store_true", help="Delete existing destination_images for affected destinations before inserting.")
    parser.add_argument("--update-images-json", action="store_true", help="Update destinations.images_json from approved rows.")
    parser.add_argument("--min-score", type=int, default=10, help="Minimum match_score to promote. Default: 10")

    parser.add_argument("--db-host", default="127.0.0.1", help="MySQL host. Default: 127.0.0.1")
    parser.add_argument("--db-port", type=int, default=3306, help="MySQL port. Default: 3306")
    parser.add_argument("--db-user", default="root", help="MySQL user. Default: root")
    parser.add_argument("--db-password", default="", help="MySQL password. Default: empty")
    parser.add_argument("--db-name", default="unudata", help="MySQL database name. Default: unudata")

    parser.add_argument("--backup-dir", default="", help="Backup directory. Default: data/image_pipeline/backup/<timestamp>")
    parser.add_argument("--log-output", default="", help="Promote log CSV path. Default: data/image_pipeline/logs/promote_images_<timestamp>.csv")
    parser.add_argument("--project-root", default=".", help="Project root. Default: current directory.")

    return parser.parse_args(argv)


def resolve_path(path_text: str, project_root: Path) -> Path:
    path = Path(path_text)
    if not path.is_absolute():
        path = (project_root / path).resolve()
    return path


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)

    project_root = Path(args.project_root).resolve()
    input_path = resolve_path(args.input, project_root)
    default_backup_dir, default_log_path = default_paths(project_root)
    backup_dir = resolve_path(args.backup_dir, project_root) if args.backup_dir else default_backup_dir
    log_path = resolve_path(args.log_output, project_root) if args.log_output else default_log_path

    _, input_rows = read_csv_rows(input_path)
    rows = selected_rows(input_rows, min_score=args.min_score)
    rag_place_ids = sorted({get_rag_place_id(row) for row in rows if get_rag_place_id(row)})

    config = DbConfig(
        host=args.db_host,
        port=args.db_port,
        user=args.db_user,
        password=args.db_password,
        database=args.db_name,
    )

    conn = connect_db(config)

    deleted_count = 0
    inserted_count = 0
    updated_json_count = 0
    destination_map: Dict[str, Dict[str, Any]] = {}
    log_rows: List[Dict[str, Any]] = []
    dest_backup_path = backup_dir / f"backup_destinations_{backup_dir.name}.csv"
    image_backup_path = backup_dir / f"backup_destination_images_{backup_dir.name}.csv"
    dest_backup_count = 0
    image_backup_count = 0

    try:
        if not table_exists(conn, "destinations"):
            raise RuntimeError("Table not found: destinations")
        if not table_exists(conn, "destination_images"):
            raise RuntimeError("Table not found: destination_images")

        require_columns(conn, "destinations", ["id", "rag_place_id", "images_json"])
        require_columns(conn, "destination_images", DESTINATION_IMAGE_INSERT_FIELDS)

        destination_map = fetch_destinations_by_rag_place_id(conn, rag_place_ids)
        affected_destination_ids = [parse_int(dest.get("id"), 0) for dest in destination_map.values() if parse_int(dest.get("id"), 0)]

        dest_backup_path, image_backup_path, dest_backup_count, image_backup_count = backup_affected_data(
            conn=conn,
            destination_map=destination_map,
            backup_dir=backup_dir,
            tag=backup_dir.name,
        )

        for row in rows:
            rag_place_id = get_rag_place_id(row)
            if rag_place_id not in destination_map:
                log_rows.append(build_log_row(row, "SKIP", "destination_not_found", ""))

        if args.apply:
            if args.replace_existing:
                deleted_count = delete_existing_images(conn, affected_destination_ids)

            inserted_count, insert_log_rows = insert_destination_images(
                conn=conn,
                rows=rows,
                destination_map=destination_map,
                replace_existing=args.replace_existing,
            )
            log_rows.extend(insert_log_rows)

            if args.update_images_json:
                images_json_by_destination = build_images_json_by_destination(rows, destination_map)
                updated_json_count = update_destinations_images_json(conn, images_json_by_destination)

            conn.commit()
        else:
            for row in rows:
                rag_place_id = get_rag_place_id(row)
                destination = destination_map.get(rag_place_id)
                if destination:
                    log_rows.append(build_log_row(row, "DRY_RUN_INSERT", "apply_not_enabled", str(destination.get("id", ""))))

        write_csv(log_path, PROMOTE_LOG_FIELDS, log_rows)

    except Exception:
        if args.apply:
            conn.rollback()
        raise
    finally:
        conn.close()

    print(f"Input: {input_path}")
    print(f"DB: {args.db_host}:{args.db_port}/{args.db_name}")
    print(f"Mode: {'APPLY' if args.apply else 'DRY_RUN'}")
    print(f"Replace existing: {args.replace_existing}")
    print(f"Update images_json: {args.update_images_json}")
    print(f"Rows in input: {len(input_rows)}")
    print(f"Rows selected for promote: {len(rows)}")
    print(f"Affected rag_place_id count: {len(rag_place_ids)}")
    print(f"Matched destination count: {len(destination_map)}")
    print()
    print("Backup")
    print(f"Destinations backed up: {dest_backup_count} -> {dest_backup_path}")
    print(f"Destination images backed up: {image_backup_count} -> {image_backup_path}")
    print()
    print("DB changes")
    print(f"Deleted existing destination_images: {deleted_count}")
    print(f"Inserted destination_images: {inserted_count}")
    print(f"Updated destinations.images_json: {updated_json_count}")
    print(f"Promote log: {log_path}")

    if not args.apply:
        print()
        print("Dry-run only. Add --apply to write to DB after checking the log and backup files.")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print()
        print("Cancelled by user.", file=sys.stderr)
        raise SystemExit(130)
