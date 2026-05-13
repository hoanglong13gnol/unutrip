# -*- coding: utf-8 -*-
"""
Create retry chunks for rows that still have no image URLs.

Input:
  data/image_pipeline/priority_ai_outputs/tier_*/tier_*_chunk_*_filled.txt

Output:
  data/image_pipeline/priority_retry_chunks/tier_1_retry_chunk_001.csv
  data/image_pipeline/priority_retry_chunks/all_missing_urls.csv

A row is considered missing if url1..url5 are all empty.
This script only reads/writes files. It does NOT touch DB.
"""

import argparse
import csv
import io
import re
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]

INPUT_DIR = ROOT_DIR / "data" / "image_pipeline" / "priority_ai_outputs"
OUT_DIR = ROOT_DIR / "data" / "image_pipeline" / "priority_retry_chunks"

HEADER = ["id", "name", "address", "province", "url1", "url2", "url3", "url4", "url5"]


def clean(value):
    if value is None:
        return ""
    return str(value).replace("\r", " ").replace("\n", " ").strip()


def extract_csv_text(raw):
    raw = raw.strip()

    # If AI output contains ```csv ... ```, extract inside.
    m = re.search(r"```(?:csv)?\s*(.*?)```", raw, flags=re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1).strip()

    return raw


def read_filled_txt(path):
    text = path.read_text(encoding="utf-8-sig", errors="ignore")
    text = extract_csv_text(text)

    if not text.strip():
        return []

    reader = csv.DictReader(io.StringIO(text))

    if not reader.fieldnames:
        return []

    normalized_fields = [clean(x).lower().lstrip("\ufeff") for x in reader.fieldnames]

    required = set(HEADER)
    if not required.issubset(set(normalized_fields)):
        print(f"[WARN] Skip invalid header: {path}")
        print(f"       fields={reader.fieldnames}")
        return []

    rows = []
    for row in reader:
        fixed = {}
        for key, value in row.items():
            k = clean(key).lower().lstrip("\ufeff")
            fixed[k] = clean(value)

        rows.append({h: fixed.get(h, "") for h in HEADER})

    return rows


def is_missing_urls(row):
    return all(not clean(row.get(f"url{i}")) for i in range(1, 6))


def output_retry_chunks(rows, chunk_size):
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    all_path = OUT_DIR / "all_missing_urls.csv"
    with all_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=HEADER)
        writer.writeheader()
        writer.writerows(rows)

    count = 0
    for i in range(0, len(rows), chunk_size):
        count += 1
        chunk = rows[i:i + chunk_size]
        out_path = OUT_DIR / f"missing_urls_retry_chunk_{count:03d}.csv"

        with out_path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=HEADER)
            writer.writeheader()
            writer.writerows(chunk)

        print(f"Created: {out_path} ({len(chunk)} rows)")

    print("")
    print("Done.")
    print(f"Missing rows : {len(rows)}")
    print(f"Retry chunks : {count}")
    print(f"All missing  : {all_path}")
    print(f"Output dir   : {OUT_DIR}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--chunk-size", type=int, default=20)
    args = parser.parse_args()

    files = sorted(INPUT_DIR.glob("tier_*/*_filled.txt"))

    if not files:
        print(f"No filled txt files found under: {INPUT_DIR}")
        return

    print(f"Found filled files: {len(files)}")

    missing = []
    seen_ids = set()

    total_rows = 0

    for path in files:
        rows = read_filled_txt(path)
        total_rows += len(rows)

        for row in rows:
            rid = clean(row.get("id"))

            if not rid:
                continue

            if rid in seen_ids:
                continue

            if is_missing_urls(row):
                missing.append(row)
                seen_ids.add(rid)

    print(f"Total rows read: {total_rows}")

    output_retry_chunks(missing, args.chunk_size)


if __name__ == "__main__":
    main()
