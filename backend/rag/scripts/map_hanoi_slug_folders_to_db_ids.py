# -*- coding: utf-8 -*-
"""
Map old Hanoi slug image folders to real destinations.rag_place_id folders.

Input:
  data/image_pipeline/downloaded/optimized/ha-noi_*

Output:
  data/image_pipeline/downloaded/optimized/<real_rag_place_id>/*.webp

Default is dry-run.
Use --execute to copy files.
"""

import argparse
import re
import shutil
import unicodedata
from pathlib import Path

import mysql.connector


ROOT = Path(r"E:\testmodelrag\smarttravel-rag-v2")
OPT = ROOT / "data" / "image_pipeline" / "downloaded" / "optimized"


SLUG_TO_NAME = {
    "ha-noi_chua-huong": "Chùa Hương",
    "ha-noi_chua-mot-cot": "Chùa Một Cột",
    "ha-noi_chua-tran-quoc": "Chùa Trấn Quốc",
    "ha-noi_den-ngoc-son": "Đền Ngọc Sơn",
    "ha-noi_ho-hoan-kiem": "Hồ Hoàn Kiếm",
    "ha-noi_ho-tay": "Hồ Tây",
    "ha-noi_hoang-thanh-thang-long": "Hoàng thành Thăng Long",
    "ha-noi_lang-chu-tich-ho-chi-minh": "Lăng Chủ tịch Hồ Chí Minh",
    "ha-noi_lang-co-duong-lam": "Làng cổ Đường Lâm",
    "ha-noi_pho-co-ha-noi": "Phố cổ Hà Nội",
    "ha-noi_thien-son-suoi-nga": "Thiên Sơn Suối Ngà",
    "ha-noi_van-mieu-quoc-tu-giam": "Văn Miếu Quốc Tử Giám",
    "ha-noi_vuon-quoc-gia-ba-vi": "Vườn quốc gia Ba Vì",
}


def clean(value):
    if value is None:
        return ""
    return str(value).strip()


def norm(value):
    value = clean(value).lower()
    value = unicodedata.normalize("NFD", value)
    value = "".join(ch for ch in value if unicodedata.category(ch) != "Mn")
    value = value.replace("đ", "d")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def connect():
    return mysql.connector.connect(
        host="127.0.0.1",
        port=3306,
        user="root",
        password="",
        database="unudata",
        charset="utf8mb4",
        use_unicode=True,
    )


def fetch_destinations():
    conn = connect()
    cur = conn.cursor(dictionary=True)

    cur.execute("""
        SELECT id, rag_place_id, name, province, address
        FROM destinations
        WHERE rag_place_id IS NOT NULL
          AND rag_place_id != ''
    """)

    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def find_match(rows, target_name):
    target_n = norm(target_name)

    # Exact name in Ha Noi first.
    exact_hanoi = [
        r for r in rows
        if norm(r.get("name")) == target_n
        and norm(r.get("province")) in {"ha noi", "hanoi"}
    ]

    if len(exact_hanoi) == 1:
        return exact_hanoi[0], "exact_name_hanoi"

    if len(exact_hanoi) > 1:
        return exact_hanoi[0], f"multiple_exact_name_hanoi:{len(exact_hanoi)}"

    # Exact name any province fallback.
    exact_any = [
        r for r in rows
        if norm(r.get("name")) == target_n
    ]

    if len(exact_any) == 1:
        return exact_any[0], "exact_name_any_province"

    # Contains fallback in Ha Noi.
    contains_hanoi = [
        r for r in rows
        if target_n in norm(r.get("name")) or norm(r.get("name")) in target_n
        if norm(r.get("province")) in {"ha noi", "hanoi"}
    ]

    if len(contains_hanoi) == 1:
        return contains_hanoi[0], "contains_name_hanoi"

    return None, f"unmatched exact_hanoi={len(exact_hanoi)} exact_any={len(exact_any)} contains_hanoi={len(contains_hanoi)}"


def next_index(dest_dir):
    existing = sorted(dest_dir.glob("*.webp"))
    max_idx = 0

    for f in existing:
        m = re.search(r"_(\d+)\.webp$", f.name)
        if m:
            max_idx = max(max_idx, int(m.group(1)))

    return max_idx + 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    rows = fetch_destinations()

    print("Mapping Hanoi slug folders to real DB rag_place_id")
    print(f"Mode: {'EXECUTE' if args.execute else 'DRY RUN'}")
    print("")

    total_copied = 0
    total_unmatched = 0

    for slug, target_name in SLUG_TO_NAME.items():
        src_dir = OPT / slug

        if not src_dir.exists():
            print(f"[SKIP] Missing source folder: {slug}")
            continue

        files = sorted(src_dir.glob("*.webp"))
        match, status = find_match(rows, target_name)

        if not match:
            total_unmatched += 1
            print(f"[UNMATCHED] {slug} -> {target_name} | {status} | files={len(files)}")
            continue

        real_rid = str(match["rag_place_id"])
        db_name = clean(match["name"])
        db_province = clean(match["province"])
        dest_dir = OPT / real_rid

        print(f"[MATCH] {slug} -> {real_rid} | {db_name} | {db_province} | {status} | files={len(files)}")

        if args.execute:
            dest_dir.mkdir(parents=True, exist_ok=True)
            idx = next_index(dest_dir)

            for f in files:
                out_name = f"{real_rid}_{idx:02d}.webp"
                out_path = dest_dir / out_name

                while out_path.exists():
                    idx += 1
                    out_name = f"{real_rid}_{idx:02d}.webp"
                    out_path = dest_dir / out_name

                shutil.copy2(f, out_path)
                print(f"  copied {f.name} -> {out_path.name}")
                idx += 1
                total_copied += 1

    print("")
    print("Done.")
    print(f"Copied images: {total_copied}")
    print(f"Unmatched folders: {total_unmatched}")

    if not args.execute:
        print("Dry-run only. Run with --execute to copy files.")


if __name__ == "__main__":
    main()
