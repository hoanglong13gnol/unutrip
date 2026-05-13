# -*- coding: utf-8 -*-
"""
Create retry chunks from priority_missing_local_images.csv.

Input:
  data/image_pipeline/reports/priority_missing_local_images.csv

Output:
  data/image_pipeline/local_missing_retry_chunks/local_missing_retry_chunk_001.csv
  ...

Output header:
  id,name,address,province,url1,url2,url3,url4,url5

This script only reads/writes CSV.
It does NOT write DB.
"""

import argparse
import csv
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]

DEFAULT_INPUT = ROOT_DIR / "data" / "image_pipeline" / "reports" / "priority_missing_local_images.csv"
DEFAULT_OUT_DIR = ROOT_DIR / "data" / "image_pipeline" / "local_missing_retry_chunks"

HEADER = ["id", "name", "address", "province", "url1", "url2", "url3", "url4", "url5"]


def clean(value):
    if value is None:
        return ""
    return str(value).replace("\r", " ").replace("\n", " ").strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--chunk-size", type=int, default=10)
    args = parser.parse_args()

    input_path = Path(args.input)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not input_path.exists():
        raise FileNotFoundError(f"Input not found: {input_path}")

    with input_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    output_rows = []
    seen = set()

    for row in rows:
        rid = clean(row.get("id"))

        if not rid or rid in seen:
            continue

        seen.add(rid)

        output_rows.append({
            "id": rid,
            "name": clean(row.get("name")),
            "address": clean(row.get("address")),
            "province": clean(row.get("province")),
            "url1": "",
            "url2": "",
            "url3": "",
            "url4": "",
            "url5": "",
        })

    chunk_count = 0

    for i in range(0, len(output_rows), args.chunk_size):
        chunk_count += 1
        chunk = output_rows[i:i + args.chunk_size]
        out_path = out_dir / f"local_missing_retry_chunk_{chunk_count:03d}.csv"

        with out_path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=HEADER)
            writer.writeheader()
            writer.writerows(chunk)

        print(f"Created: {out_path} ({len(chunk)} rows)")

    print("")
    print("Done.")
    print(f"Input rows   : {len(rows)}")
    print(f"Unique places: {len(output_rows)}")
    print(f"Chunks       : {chunk_count}")
    print(f"Output dir   : {out_dir}")


if __name__ == "__main__":
    main()
