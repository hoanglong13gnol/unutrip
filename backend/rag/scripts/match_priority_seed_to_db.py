# -*- coding: utf-8 -*-
"""
Match priority seed tier files to destinations DB.

Input seed files:
  data/image_pipeline/priority_seed/tier_1_seed.csv
  data/image_pipeline/priority_seed/tier_2_seed.csv
  data/image_pipeline/priority_seed/tier_3_seed.csv
  data/image_pipeline/priority_seed/tier_4_seed.csv

Seed header:
  seed_name,province,aliases,note

Output matched files:
  data/image_pipeline/priority_matched/tier_1_url_template.csv
  data/image_pipeline/priority_matched/tier_2_url_template.csv
  data/image_pipeline/priority_matched/tier_3_url_template.csv
  data/image_pipeline/priority_matched/tier_4_url_template.csv

Output header:
  id,name,address,province,url1,url2,url3,url4,url5

Also outputs unmatched files for manual review.

This script only reads DB.
It does NOT write to database.
"""

import argparse
import csv
import os
import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

import mysql.connector


ROOT_DIR = Path(__file__).resolve().parents[1]

SEED_DIR = ROOT_DIR / "data" / "image_pipeline" / "priority_seed"
OUT_DIR = ROOT_DIR / "data" / "image_pipeline" / "priority_matched"

OUTPUT_HEADER = [
    "id",
    "name",
    "address",
    "province",
    "url1",
    "url2",
    "url3",
    "url4",
    "url5",
]

UNMATCHED_HEADER = [
    "seed_name",
    "province",
    "aliases",
    "note",
    "match_status",
    "best_db_id",
    "best_db_name",
    "best_db_province",
    "best_score",
]


def clean(value):
    if value is None:
        return ""
    return str(value).replace("\r", " ").replace("\n", " ").strip()


def norm_text(value):
    value = clean(value).lower()
    value = unicodedata.normalize("NFD", value)
    value = "".join(ch for ch in value if unicodedata.category(ch) != "Mn")
    value = value.replace("đ", "d")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def similarity(a, b):
    a = norm_text(a)
    b = norm_text(b)
    if not a or not b:
        return 0.0

    if a == b:
        return 1.0

    # Boost when one contains the other.
    if a in b or b in a:
        short = min(len(a), len(b))
        long = max(len(a), len(b))
        return max(0.88, short / max(long, 1))

    return SequenceMatcher(None, a, b).ratio()


def split_aliases(value):
    raw = clean(value)
    if not raw:
        return []

    parts = re.split(r"[|;]", raw)
    result = []

    for part in parts:
        part = clean(part)
        if part:
            result.append(part)

    return result


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


def get_columns(cur, table_name):
    cur.execute(f"DESCRIBE {table_name}")
    return {row[0] for row in cur.fetchall()}


def select_col(cols, col_name, alias=None):
    alias = alias or col_name
    if col_name in cols:
        return f"d.{col_name} AS {alias}"
    return f"NULL AS {alias}"


def fetch_destinations(args):
    conn = connect(args)
    cur = conn.cursor()

    cols = get_columns(cur, "destinations")

    required = ["rag_place_id", "name"]
    for col in required:
        if col not in cols:
            raise RuntimeError(f"Missing required destinations column: {col}")

    select_parts = [
        select_col(cols, "id", "destination_id"),
        select_col(cols, "rag_place_id", "rag_place_id"),
        select_col(cols, "name", "name"),
        select_col(cols, "province", "province"),
        select_col(cols, "address", "address"),
        select_col(cols, "area", "area"),
        select_col(cols, "city", "city"),
        select_col(cols, "category", "category"),
        select_col(cols, "category_main", "category_main"),
        select_col(cols, "category_sub", "category_sub"),
    ]

    sql = f"""
        SELECT
            {", ".join(select_parts)}
        FROM destinations d
        WHERE d.rag_place_id IS NOT NULL
          AND d.rag_place_id <> ''
          AND d.name IS NOT NULL
          AND d.name <> ''
    """

    cur.execute(sql)
    columns = [desc[0] for desc in cur.description]
    rows = [dict(zip(columns, row)) for row in cur.fetchall()]

    cur.close()
    conn.close()

    return rows


def build_address(row):
    address = clean(row.get("address"))
    area = clean(row.get("area"))
    city = clean(row.get("city"))
    province = clean(row.get("province"))

    if address:
        return address

    parts = []

    if area:
        parts.append(area)

    if city and city not in parts:
        parts.append(city)

    if province and province not in parts:
        parts.append(province)

    return ", ".join(parts)


def read_seed_file(path):
    with Path(path).open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    required = {"seed_name", "province", "aliases", "note"}
    missing = required - set(reader.fieldnames or [])

    if missing:
        raise RuntimeError(f"{path} missing columns: {', '.join(sorted(missing))}")

    return rows


def build_dest_indexes(destinations):
    by_name_province = {}
    by_name = {}

    for row in destinations:
        name_n = norm_text(row.get("name"))
        province_n = norm_text(row.get("province"))

        if name_n:
            by_name.setdefault(name_n, []).append(row)

        if name_n and province_n:
            by_name_province.setdefault((name_n, province_n), []).append(row)

    return by_name_province, by_name


def candidate_names(seed):
    names = [clean(seed.get("seed_name"))]
    names.extend(split_aliases(seed.get("aliases")))

    result = []
    seen = set()

    for name in names:
        key = norm_text(name)
        if name and key and key not in seen:
            seen.add(key)
            result.append(name)

    return result


def choose_best_by_province(candidates, province):
    province_n = norm_text(province)

    if not candidates:
        return None

    if province_n:
        same_province = [r for r in candidates if norm_text(r.get("province")) == province_n]
        if len(same_province) == 1:
            return same_province[0]
        if len(same_province) > 1:
            return same_province[0]

    if len(candidates) == 1:
        return candidates[0]

    return None


def exact_match(seed, by_name_province, by_name):
    province = clean(seed.get("province"))

    for name in candidate_names(seed):
        name_n = norm_text(name)
        province_n = norm_text(province)

        if name_n and province_n:
            rows = by_name_province.get((name_n, province_n), [])
            if len(rows) == 1:
                return rows[0], "exact_name_province", 1.0

            if len(rows) > 1:
                return rows[0], "exact_name_province_multiple_take_first", 1.0

        rows = by_name.get(name_n, [])
        chosen = choose_best_by_province(rows, province)
        if chosen:
            return chosen, "exact_name_with_optional_province", 0.98

    return None, "", 0.0


def fuzzy_match(seed, destinations, min_score):
    province = clean(seed.get("province"))
    province_n = norm_text(province)
    names = candidate_names(seed)

    best = None
    best_score = 0.0

    for dest in destinations:
        dest_province_n = norm_text(dest.get("province"))

        # Strongly prefer same province if seed has province.
        if province_n and dest_province_n and province_n != dest_province_n:
            continue

        dest_name = clean(dest.get("name"))

        local_best = 0.0
        for name in names:
            score = similarity(name, dest_name)
            if score > local_best:
                local_best = score

        # Province match bonus.
        if province_n and dest_province_n == province_n:
            local_best += 0.03

        if local_best > best_score:
            best_score = local_best
            best = dest

    if best and best_score >= min_score:
        return best, "fuzzy_name_province", round(best_score, 4)

    return best, "unmatched" if not best else "low_score", round(best_score, 4)


def match_seed(seed, destinations, by_name_province, by_name, min_score):
    row, status, score = exact_match(seed, by_name_province, by_name)

    if row:
        return row, status, score

    return fuzzy_match(seed, destinations, min_score)


def output_row_from_destination(dest):
    return {
        "id": clean(dest.get("rag_place_id")),
        "name": clean(dest.get("name")),
        "address": build_address(dest),
        "province": clean(dest.get("province")),
        "url1": "",
        "url2": "",
        "url3": "",
        "url4": "",
        "url5": "",
    }


def unmatched_row(seed, status, best, score):
    return {
        "seed_name": clean(seed.get("seed_name")),
        "province": clean(seed.get("province")),
        "aliases": clean(seed.get("aliases")),
        "note": clean(seed.get("note")),
        "match_status": status,
        "best_db_id": clean(best.get("rag_place_id")) if best else "",
        "best_db_name": clean(best.get("name")) if best else "",
        "best_db_province": clean(best.get("province")) if best else "",
        "best_score": score,
    }


def export_one_tier(tier, args, destinations, by_name_province, by_name):
    seed_path = SEED_DIR / f"tier_{tier}_seed.csv"

    if not seed_path.exists():
        print(f"[WARN] Missing seed file: {seed_path}")
        return 0, 0

    seed_rows = read_seed_file(seed_path)

    matched_rows = []
    unmatched_rows = []
    seen_ids = set()

    for seed in seed_rows:
        dest, status, score = match_seed(
            seed=seed,
            destinations=destinations,
            by_name_province=by_name_province,
            by_name=by_name,
            min_score=args.min_score,
        )

        if dest and status not in ("unmatched", "low_score"):
            rid = clean(dest.get("rag_place_id"))
            if rid in seen_ids:
                # Same DB destination matched by multiple seed names. Keep first, log duplicate.
                unmatched_rows.append(unmatched_row(seed, "duplicate_matched_id", dest, score))
                continue

            seen_ids.add(rid)
            matched_rows.append(output_row_from_destination(dest))
        else:
            unmatched_rows.append(unmatched_row(seed, status, dest, score))

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    matched_path = OUT_DIR / f"tier_{tier}_url_template.csv"
    unmatched_path = OUT_DIR / f"tier_{tier}_unmatched.csv"

    with matched_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_HEADER)
        writer.writeheader()
        writer.writerows(matched_rows)

    with unmatched_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=UNMATCHED_HEADER)
        writer.writeheader()
        writer.writerows(unmatched_rows)

    print(f"Tier {tier}: matched={len(matched_rows)} unmatched={len(unmatched_rows)}")
    print(f"  Matched  : {matched_path}")
    print(f"  Unmatched: {unmatched_path}")

    return len(matched_rows), len(unmatched_rows)


def main(args):
    destinations = fetch_destinations(args)
    by_name_province, by_name = build_dest_indexes(destinations)

    print(f"Loaded destinations: {len(destinations)}")
    print(f"Seed dir: {SEED_DIR}")
    print(f"Output dir: {OUT_DIR}")
    print(f"Min fuzzy score: {args.min_score}")
    print("")

    total_matched = 0
    total_unmatched = 0

    for tier in args.tiers:
        matched, unmatched = export_one_tier(
            tier=tier,
            args=args,
            destinations=destinations,
            by_name_province=by_name_province,
            by_name=by_name,
        )
        total_matched += matched
        total_unmatched += unmatched

    print("")
    print("Done.")
    print(f"Total matched  : {total_matched}")
    print(f"Total unmatched: {total_unmatched}")


def parse_args():
    parser = argparse.ArgumentParser(description="Match priority seed tiers to DB destinations.")

    parser.add_argument("--tiers", nargs="+", default=["1", "2", "3", "4"], help="Tiers to process")
    parser.add_argument("--min-score", type=float, default=0.86, help="Minimum fuzzy match score")

    parser.add_argument("--db-host", default=os.getenv("DB_HOST", "127.0.0.1"))
    parser.add_argument("--db-port", type=int, default=int(os.getenv("DB_PORT", "3306")))
    parser.add_argument("--db-user", default=os.getenv("DB_USER", "root"))
    parser.add_argument("--db-password", default=os.getenv("DB_PASSWORD", ""))
    parser.add_argument("--db-name", default=os.getenv("DB_NAME", "unudata"))

    return parser.parse_args()


if __name__ == "__main__":
    main(parse_args())
