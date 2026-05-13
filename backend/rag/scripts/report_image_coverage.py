#!/usr/bin/env python
# -*- coding: utf-8 -*-

r"""
Report image coverage for UnuTrip / SmartTravel image pipeline.

Purpose:
- Read a valid image CSV produced by validate_image_urls.py.
- Optionally read a places CSV to know all places, including places with 0 valid images.
- Count valid images per rag_place_id.
- Export:
  - image_coverage.csv
  - missing_places.csv
  - needs_more_images.csv
- Do NOT import or update database.

Common usage with only valid image CSV:
python .\scripts\report_image_coverage.py ^
  --valid-images .\data\image_pipeline\valid\source_pages_page_images_raw_valid.csv

Usage with full place input list:
python .\scripts\report_image_coverage.py ^
  --places .\data\image_pipeline\input\source_pages.csv ^
  --valid-images .\data\image_pipeline\valid\source_pages_page_images_raw_valid.csv

Default outputs:
data\image_pipeline\reports\image_coverage.csv
data\image_pipeline\reports\missing_places.csv
data\image_pipeline\reports\needs_more_images.csv
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


COVERAGE_FIELDS = [
    "rag_place_id",
    "place_name",
    "province",
    "area",
    "source_page_url",
    "valid_image_count",
    "primary_image_count",
    "best_image_url",
    "coverage_status",
]

MISSING_FIELDS = [
    "rag_place_id",
    "place_name",
    "province",
    "area",
    "source_page_url",
    "valid_image_count",
    "coverage_status",
]


def clean_text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def read_csv_rows(path: Path, required: bool = True) -> Tuple[List[str], List[Dict[str, str]]]:
    if not path.exists():
        if required:
            raise FileNotFoundError(f"CSV file not found: {path}")
        return [], []

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            if required:
                raise ValueError(f"CSV has no header: {path}")
            return [], []
        return list(reader.fieldnames), list(reader)


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


def get_first_existing(row: Dict[str, str], names: Sequence[str]) -> str:
    for name in names:
        value = clean_text(row.get(name, ""))
        if value:
            return value
    return ""


def truthy(value: object) -> bool:
    text = clean_text(value).lower()
    return text in {"1", "true", "yes", "y", "primary"}


def is_valid_image_row(row: Dict[str, str]) -> bool:
    technical_status = clean_text(row.get("technical_status", "")).lower()
    if technical_status and technical_status != "valid":
        return False

    image_url = get_first_existing(row, ["final_image_url", "image_url", "url"])
    if not image_url:
        return False

    return True


def infer_coverage_status(valid_count: int, target_images: int) -> str:
    if valid_count <= 0:
        return "MISSING"
    if valid_count == 1:
        return "HAS_1"
    if valid_count == 2:
        return "HAS_2"
    if valid_count < target_images:
        return "HAS_3_PLUS_BELOW_TARGET"
    return "MEETS_TARGET"


def build_places_from_places_csv(rows: List[Dict[str, str]]) -> Dict[str, Dict[str, str]]:
    places: Dict[str, Dict[str, str]] = {}

    for row in rows:
        rag_place_id = get_first_existing(row, ["rag_place_id", "id", "place_id"])
        if not rag_place_id:
            continue

        places[rag_place_id] = {
            "rag_place_id": rag_place_id,
            "place_name": get_first_existing(row, ["place_name", "name", "title"]),
            "province": get_first_existing(row, ["province", "city"]),
            "area": get_first_existing(row, ["area", "district", "region"]),
            "source_page_url": get_first_existing(row, ["source_page_url", "source_url", "url", "page_url"]),
        }

    return places


def build_places_from_valid_images(rows: List[Dict[str, str]]) -> Dict[str, Dict[str, str]]:
    places: Dict[str, Dict[str, str]] = {}

    for row in rows:
        rag_place_id = get_first_existing(row, ["rag_place_id", "id", "place_id"])
        if not rag_place_id:
            continue

        if rag_place_id not in places:
            places[rag_place_id] = {
                "rag_place_id": rag_place_id,
                "place_name": get_first_existing(row, ["place_name", "name", "title"]),
                "province": get_first_existing(row, ["province", "city"]),
                "area": get_first_existing(row, ["area", "district", "region"]),
                "source_page_url": get_first_existing(row, ["source_page_url", "source_url", "url", "page_url"]),
            }

    return places


def summarize_coverage(
    places: Dict[str, Dict[str, str]],
    valid_image_rows: List[Dict[str, str]],
    target_images: int,
) -> Tuple[List[Dict[str, str]], Dict[str, int]]:
    valid_by_place: Dict[str, List[Dict[str, str]]] = defaultdict(list)

    for row in valid_image_rows:
        if not is_valid_image_row(row):
            continue

        rag_place_id = get_first_existing(row, ["rag_place_id", "id", "place_id"])
        if not rag_place_id:
            continue

        valid_by_place[rag_place_id].append(row)

        if rag_place_id not in places:
            places[rag_place_id] = {
                "rag_place_id": rag_place_id,
                "place_name": get_first_existing(row, ["place_name", "name", "title"]),
                "province": get_first_existing(row, ["province", "city"]),
                "area": get_first_existing(row, ["area", "district", "region"]),
                "source_page_url": get_first_existing(row, ["source_page_url", "source_url", "url", "page_url"]),
            }

    coverage_rows: List[Dict[str, str]] = []

    stats = {
        "total_places": len(places),
        "places_with_0": 0,
        "places_with_1": 0,
        "places_with_2": 0,
        "places_with_3_plus": 0,
        "places_with_5_plus": 0,
        "places_meeting_target": 0,
        "total_valid_images": 0,
    }

    for rag_place_id in sorted(places.keys()):
        place = places[rag_place_id]
        images = valid_by_place.get(rag_place_id, [])
        valid_count = len(images)
        primary_count = sum(1 for img in images if truthy(img.get("is_primary", "")))

        best_image_url = ""
        if images:
            primary_images = [img for img in images if truthy(img.get("is_primary", ""))]
            selected = primary_images[0] if primary_images else images[0]
            best_image_url = get_first_existing(selected, ["final_image_url", "image_url", "url"])

        coverage_status = infer_coverage_status(valid_count, target_images)

        if valid_count == 0:
            stats["places_with_0"] += 1
        elif valid_count == 1:
            stats["places_with_1"] += 1
        elif valid_count == 2:
            stats["places_with_2"] += 1
        else:
            stats["places_with_3_plus"] += 1

        if valid_count >= 5:
            stats["places_with_5_plus"] += 1

        if valid_count >= target_images:
            stats["places_meeting_target"] += 1

        stats["total_valid_images"] += valid_count

        coverage_rows.append(
            {
                "rag_place_id": rag_place_id,
                "place_name": place.get("place_name", ""),
                "province": place.get("province", ""),
                "area": place.get("area", ""),
                "source_page_url": place.get("source_page_url", ""),
                "valid_image_count": str(valid_count),
                "primary_image_count": str(primary_count),
                "best_image_url": best_image_url,
                "coverage_status": coverage_status,
            }
        )

    return coverage_rows, stats


def default_output_paths(project_root: Path) -> Tuple[Path, Path, Path]:
    report_dir = project_root / "data" / "image_pipeline" / "reports"
    return (
        report_dir / "image_coverage.csv",
        report_dir / "missing_places.csv",
        report_dir / "needs_more_images.csv",
    )


def print_stats(stats: Dict[str, int], target_images: int) -> None:
    total = stats["total_places"]

    def pct(value: int) -> str:
        if total <= 0:
            return "0.0%"
        return f"{value * 100 / total:.1f}%"

    print()
    print("Coverage summary")
    print(f"Total places: {total}")
    print(f"Total valid images: {stats['total_valid_images']}")
    print(f"Places with 0 images: {stats['places_with_0']} ({pct(stats['places_with_0'])})")
    print(f"Places with 1 image: {stats['places_with_1']} ({pct(stats['places_with_1'])})")
    print(f"Places with 2 images: {stats['places_with_2']} ({pct(stats['places_with_2'])})")
    print(f"Places with >=3 images: {stats['places_with_3_plus']} ({pct(stats['places_with_3_plus'])})")
    print(f"Places with >=5 images: {stats['places_with_5_plus']} ({pct(stats['places_with_5_plus'])})")
    print(f"Places meeting target >= {target_images}: {stats['places_meeting_target']} ({pct(stats['places_meeting_target'])})")


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Report image coverage from validated image CSV."
    )

    parser.add_argument(
        "--valid-images",
        required=True,
        help="Valid image CSV produced by validate_image_urls.py.",
    )

    parser.add_argument(
        "--places",
        default="",
        help="Optional full places/input CSV. Use this to count places with 0 images.",
    )

    parser.add_argument(
        "--coverage-output",
        default="",
        help="Output image coverage CSV. Default: data/image_pipeline/reports/image_coverage.csv",
    )

    parser.add_argument(
        "--missing-output",
        default="",
        help="Output missing places CSV. Default: data/image_pipeline/reports/missing_places.csv",
    )

    parser.add_argument(
        "--needs-more-output",
        default="",
        help="Output places with fewer than target images. Default: data/image_pipeline/reports/needs_more_images.csv",
    )

    parser.add_argument(
        "--target-images",
        type=int,
        default=3,
        help="Target valid images per place. Default: 3",
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

    valid_images_path = resolve_path(args.valid_images, project_root)
    places_path = resolve_path(args.places, project_root) if args.places else None

    default_coverage, default_missing, default_needs_more = default_output_paths(project_root)

    coverage_output = resolve_path(args.coverage_output, project_root) if args.coverage_output else default_coverage
    missing_output = resolve_path(args.missing_output, project_root) if args.missing_output else default_missing
    needs_more_output = resolve_path(args.needs_more_output, project_root) if args.needs_more_output else default_needs_more

    _, valid_image_rows = read_csv_rows(valid_images_path, required=True)

    if places_path:
        _, place_rows = read_csv_rows(places_path, required=True)
        places = build_places_from_places_csv(place_rows)
    else:
        places = build_places_from_valid_images(valid_image_rows)

    coverage_rows, stats = summarize_coverage(
        places=places,
        valid_image_rows=valid_image_rows,
        target_images=args.target_images,
    )

    missing_rows = [
        {
            "rag_place_id": row["rag_place_id"],
            "place_name": row["place_name"],
            "province": row["province"],
            "area": row["area"],
            "source_page_url": row["source_page_url"],
            "valid_image_count": row["valid_image_count"],
            "coverage_status": row["coverage_status"],
        }
        for row in coverage_rows
        if int(row["valid_image_count"] or "0") == 0
    ]

    needs_more_rows = [
        {
            "rag_place_id": row["rag_place_id"],
            "place_name": row["place_name"],
            "province": row["province"],
            "area": row["area"],
            "source_page_url": row["source_page_url"],
            "valid_image_count": row["valid_image_count"],
            "coverage_status": row["coverage_status"],
        }
        for row in coverage_rows
        if int(row["valid_image_count"] or "0") < args.target_images
    ]

    coverage_count = write_csv(coverage_output, COVERAGE_FIELDS, coverage_rows)
    missing_count = write_csv(missing_output, MISSING_FIELDS, missing_rows)
    needs_more_count = write_csv(needs_more_output, MISSING_FIELDS, needs_more_rows)

    print(f"Valid images input: {valid_images_path}")
    if places_path:
        print(f"Places input: {places_path}")
    else:
        print("Places input: not provided; report only covers place IDs present in valid image CSV")

    print_stats(stats, args.target_images)

    print()
    print("Files written")
    print(f"Coverage rows: {coverage_count} -> {coverage_output}")
    print(f"Missing rows: {missing_count} -> {missing_output}")
    print(f"Needs-more rows: {needs_more_count} -> {needs_more_output}")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print()
        print("Cancelled by user.", file=sys.stderr)
        raise SystemExit(130)
