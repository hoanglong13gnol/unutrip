# -*- coding: utf-8 -*-
"""
Promote downloaded local destination images to backend public folder and DB.

Input:
  data/image_pipeline/downloaded/optimized/<rag_place_id>/*.webp

Copy to:
  E:/testmodelrag/unutrip/backend/public/images/destinations/<rag_place_id>/*.webp

DB:
  - Insert into destination_images if table exists.
  - Match destinations by rag_place_id.
  - Optionally update destinations.images_json if that column exists.

Safe by default:
  - dry-run unless --execute is passed.
  - backup destination_images before replacing.
"""

import argparse
import csv
import json
import os
import shutil
from datetime import datetime
from pathlib import Path

import mysql.connector


ROOT_DIR = Path(__file__).resolve().parents[1]

DEFAULT_OPTIMIZED_DIR = ROOT_DIR / "data" / "image_pipeline" / "downloaded" / "optimized"
DEFAULT_BACKEND_IMAGE_DIR = Path(r"E:\testmodelrag\unutrip\backend\public\images\destinations")
DEFAULT_REPORT_DIR = ROOT_DIR / "data" / "image_pipeline" / "reports"
DEFAULT_BACKUP_DIR = ROOT_DIR / "data" / "image_pipeline" / "backup" / "db_import"


def now_stamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def clean(value):
    if value is None:
        return ""
    return str(value).strip()


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


def table_exists(cur, table):
    cur.execute("SHOW TABLES LIKE %s", (table,))
    return cur.fetchone() is not None


def get_columns(cur, table):
    cur.execute(f"DESCRIBE {table}")
    rows = cur.fetchall()
    return {r[0]: r for r in rows}


def backup_table(cur, table, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{table}_backup_{now_stamp()}.csv"

    cur.execute(f"SELECT * FROM {table}")
    rows = cur.fetchall()
    columns = [d[0] for d in cur.description]

    with out_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(columns)
        writer.writerows(rows)

    return out_path, len(rows)


def load_destinations(cur):
    cur.execute("DESCRIBE destinations")
    cols = {r[0] for r in cur.fetchall()}

    if "rag_place_id" not in cols:
        raise RuntimeError("destinations.rag_place_id not found")

    if "id" not in cols:
        raise RuntimeError("destinations.id not found")

    cur.execute("""
        SELECT id, rag_place_id, name
        FROM destinations
        WHERE rag_place_id IS NOT NULL
          AND rag_place_id <> ''
    """)

    result = {}
    for did, rid, name in cur.fetchall():
        result[str(rid)] = {
            "destination_id": did,
            "rag_place_id": str(rid),
            "name": clean(name),
        }

    return result


def scan_local_images(optimized_dir):
    optimized_dir = Path(optimized_dir)

    rows = []

    for place_dir in sorted([p for p in optimized_dir.iterdir() if p.is_dir()]):
        rid = place_dir.name
        files = sorted(place_dir.glob("*.webp"))

        for idx, file_path in enumerate(files, start=1):
            rows.append({
                "rag_place_id": rid,
                "source_path": file_path,
                "filename": file_path.name,
                "image_order": idx,
                "is_primary": 1 if idx == 1 else 0,
            })

    return rows


def copy_images(rows, backend_image_dir):
    backend_image_dir = Path(backend_image_dir)
    copied = 0

    for row in rows:
        rid = row["rag_place_id"]
        src = Path(row["source_path"])

        dest_dir = backend_image_dir / rid
        dest_dir.mkdir(parents=True, exist_ok=True)

        dest_path = dest_dir / src.name
        shutil.copy2(src, dest_path)

        row["backend_path"] = dest_path
        row["public_url"] = f"/images/destinations/{rid}/{src.name}"
        copied += 1

    return copied


def pick_col(cols, candidates):
    for c in candidates:
        if c in cols:
            return c
    return None


def build_insert_row(table_cols, local_row, dest_row):
    cols = set(table_cols.keys())
    data = {}

    destination_id = dest_row["destination_id"]
    rid = local_row["rag_place_id"]
    public_url = local_row["public_url"]
    backend_path = str(local_row.get("backend_path", "")).replace("\\", "/")

    if "destination_id" in cols:
        data["destination_id"] = destination_id

    if "rag_place_id" in cols:
        data["rag_place_id"] = rid

    image_url_col = pick_col(cols, ["image_url", "url", "public_url", "image", "src"])
    if image_url_col:
        data[image_url_col] = public_url

    local_path_col = pick_col(cols, ["local_path", "image_path", "path", "file_path"])
    if local_path_col:
        data[local_path_col] = backend_path

    order_col = pick_col(cols, ["image_order", "sort_order", "display_order", "order_index", "position"])
    if order_col:
        data[order_col] = local_row["image_order"]

    primary_col = pick_col(cols, ["is_primary", "is_main", "primary_image"])
    if primary_col:
        data[primary_col] = local_row["is_primary"]

    if "source" in cols:
        data["source"] = "local_downloaded"

    if "status" in cols:
        data["status"] = "active"

    if "created_at" in cols:
        data["created_at"] = datetime.now()

    if "updated_at" in cols:
        data["updated_at"] = datetime.now()

    return data


def delete_existing(cur, table_cols, rag_place_ids, destination_ids):
    cols = set(table_cols.keys())

    if "rag_place_id" in cols:
        placeholders = ",".join(["%s"] * len(rag_place_ids))
        cur.execute(f"DELETE FROM destination_images WHERE rag_place_id IN ({placeholders})", list(rag_place_ids))
        return cur.rowcount

    if "destination_id" in cols:
        placeholders = ",".join(["%s"] * len(destination_ids))
        cur.execute(f"DELETE FROM destination_images WHERE destination_id IN ({placeholders})", list(destination_ids))
        return cur.rowcount

    return 0


def insert_rows(cur, table_cols, insert_rows):
    inserted = 0

    for data in insert_rows:
        if not data:
            continue

        cols = list(data.keys())
        placeholders = ",".join(["%s"] * len(cols))
        col_sql = ",".join(f"`{c}`" for c in cols)
        sql = f"INSERT INTO destination_images ({col_sql}) VALUES ({placeholders})"
        values = [data[c] for c in cols]

        cur.execute(sql, values)
        inserted += 1

    return inserted


def update_images_json(cur, public_by_rid, destination_cols):
    if "images_json" not in destination_cols:
        return 0

    updated = 0

    for rid, urls in public_by_rid.items():
        cur.execute(
            "UPDATE destinations SET images_json = %s WHERE rag_place_id = %s",
            (json.dumps(urls, ensure_ascii=False), rid)
        )
        updated += cur.rowcount

    return updated


def write_import_preview(rows, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"destination_images_import_preview_{now_stamp()}.csv"

    header = [
        "rag_place_id",
        "source_path",
        "backend_path",
        "public_url",
        "image_order",
        "is_primary",
    ]

    with out_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()

        for row in rows:
            writer.writerow({
                "rag_place_id": row["rag_place_id"],
                "source_path": str(row["source_path"]).replace("\\", "/"),
                "backend_path": str(row.get("backend_path", "")).replace("\\", "/"),
                "public_url": row.get("public_url", ""),
                "image_order": row["image_order"],
                "is_primary": row["is_primary"],
            })

    return out_path


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--optimized-dir", default=str(DEFAULT_OPTIMIZED_DIR))
    parser.add_argument("--backend-image-dir", default=str(DEFAULT_BACKEND_IMAGE_DIR))
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR))
    parser.add_argument("--backup-dir", default=str(DEFAULT_BACKUP_DIR))

    parser.add_argument("--execute", action="store_true", help="Actually copy files and write DB")
    parser.add_argument("--replace", action="store_true", help="Delete existing destination_images for imported places first")
    parser.add_argument("--update-images-json", action="store_true", help="Update destinations.images_json if column exists")

    parser.add_argument("--db-host", default=os.getenv("DB_HOST", "127.0.0.1"))
    parser.add_argument("--db-port", type=int, default=int(os.getenv("DB_PORT", "3306")))
    parser.add_argument("--db-user", default=os.getenv("DB_USER", "root"))
    parser.add_argument("--db-password", default=os.getenv("DB_PASSWORD", ""))
    parser.add_argument("--db-name", default=os.getenv("DB_NAME", "unudata"))

    args = parser.parse_args()

    optimized_dir = Path(args.optimized_dir)
    backend_image_dir = Path(args.backend_image_dir)
    report_dir = Path(args.report_dir)
    backup_dir = Path(args.backup_dir)

    if not optimized_dir.exists():
        raise FileNotFoundError(f"Optimized dir not found: {optimized_dir}")

    local_rows = scan_local_images(optimized_dir)

    print(f"Optimized dir: {optimized_dir}")
    print(f"Local images found: {len(local_rows)}")
    print(f"Local places found: {len(set(r['rag_place_id'] for r in local_rows))}")

    conn = connect(args)
    cur = conn.cursor()

    if not table_exists(cur, "destinations"):
        raise RuntimeError("Table destinations not found")

    if not table_exists(cur, "destination_images"):
        raise RuntimeError("Table destination_images not found")

    destinations = load_destinations(cur)
    destination_image_cols = get_columns(cur, "destination_images")
    destination_cols = get_columns(cur, "destinations")

    matched_rows = []
    missing_dest = []

    for row in local_rows:
        rid = row["rag_place_id"]
        if rid not in destinations:
            missing_dest.append(rid)
            continue
        matched_rows.append(row)

    print(f"Matched images: {len(matched_rows)}")
    print(f"Missing destination mappings: {len(set(missing_dest))}")

    if not args.execute:
        print("")
        print("DRY RUN ONLY. No files copied, no DB changes.")
        print("Run with --execute to apply.")
        cur.close()
        conn.close()
        return

    copied = copy_images(matched_rows, backend_image_dir)
    preview_path = write_import_preview(matched_rows, report_dir)

    backup_path, backup_count = backup_table(cur, "destination_images", backup_dir)

    rag_place_ids = sorted(set(r["rag_place_id"] for r in matched_rows))
    destination_ids = sorted(set(destinations[rid]["destination_id"] for rid in rag_place_ids))

    deleted = 0
    if args.replace:
        deleted = delete_existing(cur, destination_image_cols, rag_place_ids, destination_ids)

    insert_payload = []

    for row in matched_rows:
        dest = destinations[row["rag_place_id"]]
        insert_payload.append(build_insert_row(destination_image_cols, row, dest))

    inserted = insert_rows(cur, destination_image_cols, insert_payload)

    public_by_rid = {}
    for row in matched_rows:
        public_by_rid.setdefault(row["rag_place_id"], []).append(row["public_url"])

    images_json_updated = 0
    if args.update_images_json:
        images_json_updated = update_images_json(cur, public_by_rid, destination_cols)

    conn.commit()
    cur.close()
    conn.close()

    print("")
    print("IMPORT DONE.")
    print(f"Copied files           : {copied}")
    print(f"Backup destination_images: {backup_path} ({backup_count} rows)")
    print(f"Deleted old rows       : {deleted}")
    print(f"Inserted rows          : {inserted}")
    print(f"Updated images_json    : {images_json_updated}")
    print(f"Preview CSV            : {preview_path}")
    print(f"Backend image dir      : {backend_image_dir}")


if __name__ == "__main__":
    main()
