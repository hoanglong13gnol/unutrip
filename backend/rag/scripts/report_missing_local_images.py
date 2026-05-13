# -*- coding: utf-8 -*-
"""
Report missing local images by comparing priority matched templates
against downloaded optimized local images.

Input:
  data/image_pipeline/priority_matched/tier_1_url_template.csv
  data/image_pipeline/priority_matched/tier_2_url_template.csv
  ...
  data/image_pipeline/downloaded/optimized/<rag_place_id>/*.webp

Output:
  data/image_pipeline/reports/priority_local_image_coverage.csv
  data/image_pipeline/reports/priority_missing_local_images.csv

This script does NOT write DB.
"""

import argparse
import csv
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]

MATCHED_DIR = ROOT_DIR / "data" / "image_pipeline" / "priority_matched"
OPTIMIZED_DIR = ROOT_DIR / "data" / "image_pipeline" / "downloaded" / "optimized"
REPORT_DIR = ROOT_DIR / "data" / "image_pipeline" / "reports"

COVERAGE_OUT = REPORT_DIR / "priority_local_image_coverage.csv"
MISSING_OUT = REPORT_DIR / "priority_missing_local_images.csv"

HEADER = [
    "tier",
    "id",
    "name",
    "address",
    "province",
    "local_image_count",
    "status",
    "image_files",
]


def clean(value):
    if value is None:
        return ""
    return str(value).replace("\r", " ").replace("\n", " ").strip()


def read_template(tier):
    path = MATCHED_DIR / f"tier_{tier}_url_template.csv"

    if not path.exists():
        return []

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    for row in rows:
        row["_tier"] = str(tier)

    return rows


def local_files_for(rag_place_id):
    place_dir = OPTIMIZED_DIR / rag_place_id

    if not place_dir.exists():
        return []

    return sorted(place_dir.glob("*.webp"))


def status_from_count(count):
    if count <= 0:
        return "missing"
    if count == 1:
        return "has_1"
    if count == 2:
        return "has_2"
    if count >= 3:
        return "has_3_plus"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tiers", nargs="+", default=["1", "2", "3", "4"])
    args = parser.parse_args()

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    coverage_rows = []
    missing_rows = []

    for tier in args.tiers:
        rows = read_template(tier)

        for row in rows:
            rid = clean(row.get("id"))
            files = local_files_for(rid)
            count = len(files)

            image_files = "|".join(
                str(f.relative_to(ROOT_DIR)).replace("\\", "/")
                for f in files
            )

            out = {
                "tier": tier,
                "id": rid,
                "name": clean(row.get("name")),
                "address": clean(row.get("address")),
                "province": clean(row.get("province")),
                "local_image_count": count,
                "status": status_from_count(count),
                "image_files": image_files,
            }

            coverage_rows.append(out)

            if count == 0:
                missing_rows.append(out)

    with COVERAGE_OUT.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=HEADER)
        writer.writeheader()
        writer.writerows(coverage_rows)

    with MISSING_OUT.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=HEADER)
        writer.writeheader()
        writer.writerows(missing_rows)

    total = len(coverage_rows)
    missing = len(missing_rows)
    has_1 = sum(1 for r in coverage_rows if int(r["local_image_count"]) == 1)
    has_2 = sum(1 for r in coverage_rows if int(r["local_image_count"]) == 2)
    has_3_plus = sum(1 for r in coverage_rows if int(r["local_image_count"]) >= 3)

    print("Priority local image report created.")
    print(f"Total priority places : {total}")
    print(f"Missing local images  : {missing}")
    print(f"Has 1 image           : {has_1}")
    print(f"Has 2 images          : {has_2}")
    print(f"Has >=3 images        : {has_3_plus}")
    print(f"Coverage output       : {COVERAGE_OUT}")
    print(f"Missing output        : {MISSING_OUT}")


if __name__ == "__main__":
    main()
