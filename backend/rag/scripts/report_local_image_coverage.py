# -*- coding: utf-8 -*-
"""
Report local downloaded image coverage.

Input:
  data/image_pipeline/downloaded/optimized/<rag_place_id>/*.webp

Output:
  data/image_pipeline/reports/local_image_coverage.csv

This script only reads local files.
It does NOT write DB.
"""

import csv
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
OPTIMIZED_DIR = ROOT_DIR / "data" / "image_pipeline" / "downloaded" / "optimized"
REPORT_DIR = ROOT_DIR / "data" / "image_pipeline" / "reports"
OUT_PATH = REPORT_DIR / "local_image_coverage.csv"


HEADER = [
    "rag_place_id",
    "local_image_count",
    "primary_candidate",
    "image_files",
    "total_size_bytes",
]


def main():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    rows = []

    if not OPTIMIZED_DIR.exists():
        print(f"Missing dir: {OPTIMIZED_DIR}")
        return

    for place_dir in sorted([p for p in OPTIMIZED_DIR.iterdir() if p.is_dir()]):
        files = sorted(place_dir.glob("*.webp"))
        if not files:
            continue

        total_size = sum(f.stat().st_size for f in files)
        image_files = "|".join(str(f.relative_to(ROOT_DIR)).replace("\\", "/") for f in files)

        rows.append({
            "rag_place_id": place_dir.name,
            "local_image_count": len(files),
            "primary_candidate": str(files[0].relative_to(ROOT_DIR)).replace("\\", "/"),
            "image_files": image_files,
            "total_size_bytes": total_size,
        })

    with OUT_PATH.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=HEADER)
        writer.writeheader()
        writer.writerows(rows)

    print("Local image coverage report created.")
    print(f"Places with local images: {len(rows)}")
    print(f"Total local images: {sum(int(r['local_image_count']) for r in rows)}")
    print(f"Output: {OUT_PATH}")


if __name__ == "__main__":
    main()
