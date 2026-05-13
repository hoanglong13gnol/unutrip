# -*- coding: utf-8 -*-
"""
Normalize tier image URL outputs.

Input:
  data/image_pipeline/priority_ai_outputs/**/*.txt
  data/image_pipeline/priority_retry_outputs/**/*.txt

Each TXT may contain raw CSV or CSV inside a code block.

Input CSV header:
  id,name,address,province,url1,url2,url3,url4,url5

Output:
  data/image_pipeline/raw/priority_image_candidates.csv

Output CSV header:
  rag_place_id,place_name,image_url,source_page_url,source,credit,license_note,
  image_order,is_primary,batch_code,provider,confidence,need_human_check,
  candidate_status,ai_note

This script only reads/writes files.
It does NOT write to database.
"""

import argparse
import csv
import io
import re
from pathlib import Path
from urllib.parse import urlparse


ROOT_DIR = Path(__file__).resolve().parents[1]

DEFAULT_INPUT_DIRS = [
    ROOT_DIR / "data" / "image_pipeline" / "priority_ai_outputs",
    ROOT_DIR / "data" / "image_pipeline" / "priority_retry_outputs",
]

DEFAULT_OUTPUT = ROOT_DIR / "data" / "image_pipeline" / "raw" / "priority_image_candidates.csv"

INPUT_HEADER = ["id", "name", "address", "province", "url1", "url2", "url3", "url4", "url5"]

OUTPUT_HEADER = [
    "rag_place_id",
    "place_name",
    "image_url",
    "source_page_url",
    "source",
    "credit",
    "license_note",
    "image_order",
    "is_primary",
    "batch_code",
    "provider",
    "confidence",
    "need_human_check",
    "candidate_status",
    "ai_note",
]


def clean(value):
    if value is None:
        return ""
    return str(value).replace("\r", " ").replace("\n", " ").strip()


def extract_csv_text(raw):
    raw = raw.strip()

    # Extract CSV from ```csv ... ``` if present.
    m = re.search(r"```(?:csv)?\s*(.*?)```", raw, flags=re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1).strip()

    return raw


def normalize_fieldname(name):
    return clean(name).lower().lstrip("\ufeff")


def read_rows_from_txt(path):
    text = path.read_text(encoding="utf-8-sig", errors="ignore")
    text = extract_csv_text(text)

    if not text.strip():
        return []

    reader = csv.DictReader(io.StringIO(text))

    if not reader.fieldnames:
        print(f"[WARN] Empty/no header: {path}")
        return []

    fields = [normalize_fieldname(x) for x in reader.fieldnames]
    required = set(INPUT_HEADER)

    if not required.issubset(set(fields)):
        print(f"[WARN] Invalid header, skipped: {path}")
        print(f"       fields={reader.fieldnames}")
        return []

    rows = []

    for row in reader:
        fixed = {}
        for key, value in row.items():
            fixed[normalize_fieldname(key)] = clean(value)

        rows.append({h: fixed.get(h, "") for h in INPUT_HEADER})

    return rows


def infer_source(url):
    host = urlparse(url).netloc.lower()

    if "wikimedia.org" in host or "wikipedia.org" in host:
        return "Wikimedia Commons"
    if "mia.vn" in host:
        return "MIA.vn"
    if "vinwonders.com" in host:
        return "VinWonders"
    if "traveloka" in host or "imagekit.io" in host:
        return "Traveloka"
    if "thamhiemmekong.com" in host:
        return "Thám Hiểm Mekong"
    if "luhanhvietnam.com.vn" in host:
        return "Lữ Hành Việt Nam"
    if "vntrip.vn" in host:
        return "VNTrip"
    if "52hz.vn" in host:
        return "52Hz"
    if "vnecdn.net" in host or "vnexpress.net" in host:
        return "VnExpress"

    return host or "unknown"


def source_page_from_image(url):
    # For Wikimedia Special:FilePath, source page can be same URL for now.
    return url


def batch_code_from_path(path):
    stem = path.stem

    # tier_1_chunk_001_filled -> tier_1_chunk_001
    stem = re.sub(r"_filled$", "", stem)

    # missing_urls_retry_chunk_001_filled -> missing_urls_retry_chunk_001
    stem = re.sub(r"_filled$", "", stem)

    parent = path.parent.name

    if parent.startswith("tier_"):
        return f"{parent}_{stem}"

    return stem


def normalize_all(args):
    input_dirs = [Path(p) for p in args.input_dirs] if args.input_dirs else DEFAULT_INPUT_DIRS
    output_path = Path(args.output) if args.output else DEFAULT_OUTPUT
    output_path.parent.mkdir(parents=True, exist_ok=True)

    all_files = []
    for d in input_dirs:
        if d.exists():
            all_files.extend(sorted(d.glob("**/*.txt")))

    if not all_files:
        print("No .txt files found.")
        for d in input_dirs:
            print(f"Checked: {d}")
        return

    candidates = []
    seen = set()

    total_place_rows = 0
    total_urls = 0
    skipped_empty_url = 0
    skipped_duplicate = 0

    for path in all_files:
        rows = read_rows_from_txt(path)
        if not rows:
            continue

        batch_code = batch_code_from_path(path)

        for row in rows:
            total_place_rows += 1

            rid = clean(row.get("id"))
            name = clean(row.get("name"))

            if not rid or not name:
                continue

            image_order = 0

            for idx in range(1, 6):
                url = clean(row.get(f"url{idx}"))

                if not url:
                    skipped_empty_url += 1
                    continue

                key = (rid.lower(), url.lower())

                if key in seen:
                    skipped_duplicate += 1
                    continue

                seen.add(key)
                image_order += 1
                total_urls += 1

                source = infer_source(url)

                candidates.append({
                    "rag_place_id": rid,
                    "place_name": name,
                    "image_url": url,
                    "source_page_url": source_page_from_image(url),
                    "source": source,
                    "credit": "",
                    "license_note": "Cần kiểm tra quyền sử dụng",
                    "image_order": image_order,
                    "is_primary": 1 if image_order == 1 else 0,
                    "batch_code": batch_code,
                    "provider": "priority_ai_url_fill",
                    "confidence": "medium",
                    "need_human_check": 1,
                    "candidate_status": "pending",
                    "ai_note": f"Normalized from {path.name}",
                })

    with output_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_HEADER)
        writer.writeheader()
        writer.writerows(candidates)

    print("")
    print("Normalize finished.")
    print(f"Input txt files       : {len(all_files)}")
    print(f"Place rows read       : {total_place_rows}")
    print(f"Candidate URLs        : {len(candidates)}")
    print(f"Skipped empty url     : {skipped_empty_url}")
    print(f"Skipped duplicate URL : {skipped_duplicate}")
    print(f"Output                : {output_path}")


def parse_args():
    parser = argparse.ArgumentParser(description="Normalize tier url1..url5 TXT outputs to image candidate CSV.")
    parser.add_argument("--input-dirs", nargs="*", default=[], help="Input dirs containing .txt files")
    parser.add_argument("--output", default="", help="Output candidate CSV path")
    return parser.parse_args()


if __name__ == "__main__":
    normalize_all(parse_args())
