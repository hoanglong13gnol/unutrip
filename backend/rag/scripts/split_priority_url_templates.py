# -*- coding: utf-8 -*-
"""
Split matched tier url_template CSV files into smaller prompt chunks.

Input:
  data/image_pipeline/priority_matched/tier_1_url_template.csv
  ...

Output:
  data/image_pipeline/priority_prompt_chunks/tier_1/tier_1_chunk_001.csv
  ...

This script only reads/writes CSV files.
"""

import argparse
import csv
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
IN_DIR = ROOT_DIR / "data" / "image_pipeline" / "priority_matched"
OUT_DIR = ROOT_DIR / "data" / "image_pipeline" / "priority_prompt_chunks"


def split_file(tier: str, chunk_size: int):
    in_path = IN_DIR / f"tier_{tier}_url_template.csv"

    if not in_path.exists():
        print(f"[WARN] Missing: {in_path}")
        return 0

    with in_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames or []

    tier_out = OUT_DIR / f"tier_{tier}"
    tier_out.mkdir(parents=True, exist_ok=True)

    count = 0

    for i in range(0, len(rows), chunk_size):
        chunk = rows[i:i + chunk_size]
        count += 1
        out_path = tier_out / f"tier_{tier}_chunk_{count:03d}.csv"

        with out_path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(chunk)

        print(f"Created: {out_path} ({len(chunk)} rows)")

    return count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tiers", nargs="+", default=["1", "2", "3", "4"])
    parser.add_argument("--chunk-size", type=int, default=20)
    args = parser.parse_args()

    total = 0
    for tier in args.tiers:
        total += split_file(tier, args.chunk_size)

    print("")
    print(f"Done. Total chunks: {total}")
    print(f"Output dir: {OUT_DIR}")


if __name__ == "__main__":
    main()
