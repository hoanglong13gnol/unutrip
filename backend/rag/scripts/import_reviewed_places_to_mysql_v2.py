# -*- coding: utf-8 -*-
"""
Import reviewed SmartTravel / UnuTrip places into MySQL schema v2.

Schema target:
  - destinations: app serving table for Android / Node.js
  - rag_places: AI / RAG / Gemini table with full reviewed data

Rules:
  - Source of truth: data/processed/places_app_reviewed.json
  - Upsert by place_id / rag_place_id
  - Do NOT generate random images
  - Do NOT write picsum.photos
  - Preserve existing real images in destinations.images_json
  - If no image exists, keep images_json = []
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    import mysql.connector
    MYSQL_CONNECTOR_IMPORT_ERROR = None
except ImportError as exc:
    mysql = None
    MYSQL_CONNECTOR_IMPORT_ERROR = exc


DEFAULT_DB_HOST = "127.0.0.1"
DEFAULT_DB_PORT = 3306
DEFAULT_DB_USER = "root"
DEFAULT_DB_PASSWORD = ""
DEFAULT_DB_NAME = "unudata"

# Canonical app categories used by Android/backend filters.
# Keep DB/API values in English lowercase codes; only Android UI should translate them.
CANONICAL_APP_CATEGORIES = {
    "beach",
    "mountain",
    "city",
    "heritage",
    "nature",
    "checkin",
    "food",
    "culture",
    "religious",
    "other",
}

# Direct aliases for already-normalized/category-code style values.
APP_CATEGORY_ALIAS_MAP = {
    "beach": "beach",
    "beaches": "beach",
    "bien": "beach",
    "bien_dao": "beach",
    "mountain": "mountain",
    "mountains": "mountain",
    "nui": "mountain",
    "rung_nui": "mountain",
    "city": "city",
    "urban": "city",
    "do_thi": "city",
    "street": "city",
    "market": "city",
    "landmark": "city",
    "heritage": "heritage",
    "historical": "heritage",
    "history": "heritage",
    "di_tich": "heritage",
    "di_tich_van_hoa": "heritage",
    "di_tich_lich_su": "heritage",
    "museum": "heritage",
    "nature": "nature",
    "natural": "nature",
    "thien_nhien": "nature",
    "thien_nhien_sinh_thai": "nature",
    "sinh_thai_tu_nhien": "nature",
    "checkin": "checkin",
    "check_in": "checkin",
    "check-in": "checkin",
    "entertainment": "checkin",
    "giai_tri": "checkin",
    "park": "checkin",
    "theme_park": "checkin",
    "food": "food",
    "am_thuc": "food",
    "culture": "culture",
    "cultural": "culture",
    "van_hoa": "culture",
    "van_hoa_cong_dong": "culture",
    "lang_nghe": "culture",
    "village": "culture",
    "religious": "religious",
    "religion": "religious",
    "spiritual": "religious",
    "tam_linh": "religious",
    "ton_giao": "religious",
    "other": "other",
}


def strip_vietnamese_accents(value: Any) -> str:
    text = "" if value is None else str(value)
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return text.replace("đ", "d").replace("Đ", "D")


def normalize_token_text(value: Any) -> str:
    text = strip_vietnamese_accents(value).lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_category_key(value: Any) -> str:
    return normalize_token_text(value).replace(" ", "_")


def has_phrase(text: str, phrases: Iterable[str]) -> bool:
    padded = f" {text} "
    return any(f" {phrase} " in padded for phrase in phrases)


def joined_category_text(item: Dict[str, Any]) -> Tuple[str, str]:
    """Return normalized category text and normalized name text separately."""
    category_fields = [
        item.get("category_main"),
        item.get("category_sub"),
        item.get("category_main_norm"),
        item.get("category_sub_norm"),
    ]
    name_fields = [item.get("name"), item.get("aliases_json")]
    return normalize_token_text(" ".join(str(v or "") for v in category_fields)), normalize_token_text(
        " ".join(str(v or "") for v in name_fields)
    )


RAG_PLACE_COLUMNS = [
    "place_id",
    "destination_id",
    "name",
    "aliases_json",
    "province",
    "city",
    "area",
    "destination_group",
    "address",
    "latitude",
    "longitude",
    "category_main",
    "category_sub",
    "category_main_norm",
    "category_sub_norm",
    "tags_json",
    "interest_tags_json",
    "suitable_for_json",
    "avoid_for_json",
    "description",
    "short_description",
    "open_time",
    "close_time",
    "best_time_of_day_json",
    "suggested_slot",
    "slot_norm",
    "duration_minutes",
    "is_night_activity",
    "is_free",
    "entry_fee_min",
    "entry_fee_max",
    "budget_level",
    "budget_level_norm",
    "price_note",
    "walking_level",
    "walking_level_norm",
    "activity_level",
    "activity_level_norm",
    "elderly_friendly",
    "elderly_friendly_norm",
    "kid_friendly",
    "kid_friendly_norm",
    "nearby_area_json",
    "transport_suggestion_json",
    "quality_score",
    "recommended_use",
    "recommended_use_norm",
    "is_generic",
    "must_not_schedule_as_main",
    "requires_realtime_check",
    "realtime_fields_json",
    "source",
    "source_url",
    "last_updated",
    "is_active",
    "search_text",
    "raw_json",
]


def load_dotenv_if_exists(project_root: Path) -> None:
    """Minimal .env loader. Does not override existing environment variables."""
    env_paths = [
        project_root / ".env",
        project_root.parent / "unutrip" / "backend" / ".env",
        Path(r"E:\testmodelrag\unutrip\backend\.env"),
    ]

    for env_path in env_paths:
        if not env_path.exists():
            continue

        try:
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                os.environ.setdefault(key, value)
        except Exception as exc:
            print(f"WARNING: Could not read .env file {env_path}: {exc}")


def get_project_root() -> Path:
    """Assume this file is inside smarttravel-rag-v2/scripts."""
    return Path(__file__).resolve().parents[1]


def read_json_array(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError(f"Expected JSON array in {path}, got {type(data).__name__}")

    return data


def as_json_text(value: Any, default: str = "[]") -> str:
    """
    Convert field to JSON text safely.

    Reviewed dataset sometimes stores JSON fields as strings like:
      '["gia đình", "cặp đôi"]'

    If value is already a JSON string, keep normalized JSON text.
    If value is list/dict/bool/number, dump it.
    """
    if value is None:
        return default

    if isinstance(value, str):
        s = value.strip()
        if not s:
            return default
        try:
            parsed = json.loads(s)
            return json.dumps(parsed, ensure_ascii=False)
        except Exception:
            # Not valid JSON string; store as a JSON array with one string to avoid invalid JSON cache.
            return json.dumps([s], ensure_ascii=False)

    return json.dumps(value, ensure_ascii=False)


def as_raw_json_text(item: Dict[str, Any]) -> str:
    return json.dumps(item, ensure_ascii=False, sort_keys=True)


def as_bool_int(value: Any, default: int = 0) -> int:
    if value is None:
        return default

    if isinstance(value, bool):
        return 1 if value else 0

    if isinstance(value, (int, float)):
        return 1 if value else 0

    if isinstance(value, str):
        s = value.strip().lower()
        if s in {"true", "1", "yes", "y", "co", "có"}:
            return 1
        if s in {"false", "0", "no", "n", "khong", "không"}:
            return 0

    return default


def as_int(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except Exception:
        return None


def as_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except Exception:
        return None


def as_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return str(value)


def normalize_app_category(item: Dict[str, Any]) -> str:
    """
    Normalize reviewed RAG taxonomy into app/backend category codes.

    Important design rule:
      - destinations.category is for Android/backend filters.
      - category_main/category_sub remain available for detailed RAG/admin taxonomy.
      - Do not store Vietnamese labels in destinations.category.
    """
    category_main = as_text(item.get("category_main")) or ""
    category_sub = as_text(item.get("category_sub")) or ""
    category_main_norm = as_text(item.get("category_main_norm")) or category_main
    category_sub_norm = as_text(item.get("category_sub_norm")) or category_sub

    main_key = normalize_category_key(category_main_norm or category_main)
    sub_key = normalize_category_key(category_sub_norm or category_sub)

    if main_key in APP_CATEGORY_ALIAS_MAP:
        mapped = APP_CATEGORY_ALIAS_MAP[main_key]
        # Broad nature records are refined below using category_sub/name.
        if mapped not in {"nature", "other"}:
            return mapped

    category_text, name_text = joined_category_text(item)
    combined_text = f"{category_text} {name_text}".strip()

    # Strong religious signals. Keep this before heritage because many temples are historical too.
    if has_phrase(
        combined_text,
        [
            "tam linh",
            "ton giao",
            "chua",
            "thien vien",
            "den",
            "phu",
            "mieu",
            "nha tho",
            "giao xu",
            "thanh that",
            "tu vien",
            "lang ong",
            "lang tam",
            "thap cham",
        ],
    ):
        return "religious"

    if has_phrase(
        category_text,
        ["di tich", "lich su", "bao tang", "nha tu", "chien khu", "can cu", "dia dao", "thanh co", "khu luu niem", "museum", "heritage"],
    ):
        return "heritage"

    if has_phrase(category_text, ["am thuc", "dac san", "khu am thuc", "cho dem", "food"]):
        return "food"

    # Use raw Vietnamese text for beach to avoid false positives such as "Tịnh Biên".
    raw_category_text = f" {category_main} {category_sub} ".lower()
    raw_name_text = f" {as_text(item.get('name')) or ''} ".lower()
    if any(
        phrase in raw_category_text or phrase in raw_name_text
        for phrase in [" biển", "bãi biển", "bãi tắm", "biển đảo", "đảo", "vịnh", "cù lao", "hòn ", "mũi ", "đầm phá", "cảng biển"]
    ):
        return "beach"

    # Water-delta / wetland / garden ecology should remain nature instead of being forced into mountain.
    if has_phrase(
        category_text,
        ["song nuoc", "rung tram", "rung ngap man", "dat ngap nuoc", "miet vuon", "vuon trai cay", "dam sen"],
    ):
        return "nature"

    if has_phrase(
        category_text,
        ["thac", "hang", "cao nguyen", "doi che", "doi cat", "deo", "dinh nui", "nui rung", "rung nui", "ho thac", "suoi", "waterfall", "cave", "lake"],
    ):
        return "mountain"

    if has_phrase(name_text, ["nui", "thac", "hang", "cao nguyen", "doi che", "doi cat", "deo", "suoi"]):
        return "mountain"

    if has_phrase(
        category_text,
        [
            "cong vien",
            "khu vui choi",
            "check in",
            "giai tri",
            "theme park",
            "khu du lich",
            "vui choi",
            "resort",
            "nghi duong",
            "quang truong",
            "pho di bo",
            "cau",
            "bieu tuong",
            # Tourist transport/scenic access points should stay visible in app filters.
            # They are not the same as urban transport infrastructure, so map them to checkin.
            "giao thong canh quan",
            "ben tau",
            "ben tau du lich",
            "ben pha",
            "cang pha",
            "cang tau",
        ],
    ):
        return "checkin"

    if has_phrase(
        category_text,
        ["van hoa", "cong dong", "lang nghe", "ban lang", "cho phien", "cho noi", "le hoi", "dan gian", "nha rong", "village", "culture"],
    ):
        return "culture"

    if has_phrase(category_text, ["thanh pho", "do thi", "pho co", "cho", "market", "street", "nha hat", "kien truc", "landmark"]):
        return "city"

    if main_key in APP_CATEGORY_ALIAS_MAP:
        return APP_CATEGORY_ALIAS_MAP[main_key]
    if sub_key in APP_CATEGORY_ALIAS_MAP:
        return APP_CATEGORY_ALIAS_MAP[sub_key]

    if has_phrase(category_text, ["thien nhien", "sinh thai", "danh thang", "rung", "vuon quoc gia", "nature"]):
        return "nature"

    return "other"

def merge_tags_for_app(item: Dict[str, Any]) -> str:
    merged: List[str] = []

    for field in ["tags_json", "interest_tags_json", "suitable_for_json"]:
        raw = item.get(field)
        if raw is None:
            continue

        try:
            if isinstance(raw, str):
                parsed = json.loads(raw)
            else:
                parsed = raw
        except Exception:
            parsed = [raw]

        if isinstance(parsed, list):
            for value in parsed:
                if value is None:
                    continue
                text = str(value).strip()
                if text and text not in merged:
                    merged.append(text)
        else:
            text = str(parsed).strip()
            if text and text not in merged:
                merged.append(text)

    return json.dumps(merged, ensure_ascii=False)


def is_real_images_json(value: Optional[str]) -> bool:
    """
    True if destinations.images_json contains at least one non-picsum image URL/item.
    Empty, null, invalid, and picsum-only values are not considered real images.
    """
    if value is None:
        return False

    s = str(value).strip()
    if not s or s == "[]":
        return False

    try:
        parsed = json.loads(s)
    except Exception:
        return "picsum.photos" not in s

    if not isinstance(parsed, list) or len(parsed) == 0:
        return False

    text = json.dumps(parsed, ensure_ascii=False)
    if "picsum.photos" in text:
        return False

    return True


def connect_mysql(args: argparse.Namespace):
    if MYSQL_CONNECTOR_IMPORT_ERROR is not None:
        raise RuntimeError(
            "Missing package mysql-connector-python. Install it with: pip install mysql-connector-python"
        ) from MYSQL_CONNECTOR_IMPORT_ERROR

    return mysql.connector.connect(
        host=args.db_host,
        port=args.db_port,
        user=args.db_user,
        password=args.db_password,
        database=args.db_name,
        charset="utf8mb4",
        use_unicode=True,
    )


def get_existing_destination(cursor, place_id: str) -> Optional[Dict[str, Any]]:
    cursor.execute(
        """
        SELECT id, images_json
        FROM destinations
        WHERE rag_place_id = %s
        LIMIT 1
        """,
        (place_id,),
    )
    row = cursor.fetchone()
    if not row:
        return None
    return {"id": row[0], "images_json": row[1]}


def upsert_destination(cursor, item: Dict[str, Any]) -> int:
    place_id = as_text(item.get("place_id"))
    if not place_id:
        raise ValueError("Missing place_id")

    existing = get_existing_destination(cursor, place_id)

    # Preserve real images. Never generate or overwrite random images.
    if existing and is_real_images_json(existing.get("images_json")):
        images_json = existing["images_json"]
    else:
        images_json = "[]"

    values = {
        "rag_place_id": place_id,
        "name": as_text(item.get("name")) or "",
        "description": as_text(item.get("description")) or "",
        "short_description": as_text(item.get("short_description")),
        "address": as_text(item.get("address")),
        "city": as_text(item.get("city")),
        "province": as_text(item.get("province")),
        "area": as_text(item.get("area")),
        "latitude": as_float(item.get("latitude")),
        "longitude": as_float(item.get("longitude")),
        "category": normalize_app_category(item),
        "category_main": as_text(item.get("category_main")),
        "category_sub": as_text(item.get("category_sub")),
        "images_json": images_json,
        "rating": as_float(item.get("quality_score")) or 0,
        "review_count": 0,
        "open_time": as_text(item.get("open_time")),
        "close_time": as_text(item.get("close_time")),
        "entry_fee": as_float(item.get("entry_fee_min")),
        "budget_level": as_text(item.get("budget_level_norm")) or as_text(item.get("budget_level")),
        "walking_level": as_text(item.get("walking_level_norm")) or as_text(item.get("walking_level")),
        "kid_friendly": as_bool_int(item.get("kid_friendly_norm")),
        "elderly_friendly": as_bool_int(item.get("elderly_friendly_norm")),
        "recommended_use": as_text(item.get("recommended_use_norm")) or as_text(item.get("recommended_use")),
        "tags_json": merge_tags_for_app(item),
        "is_active": as_bool_int(item.get("is_active"), default=1),
    }

    columns = list(values.keys())
    placeholders = ", ".join(["%s"] * len(columns))
    column_sql = ", ".join(columns)

    update_columns = [col for col in columns if col != "rag_place_id"]
    update_sql = ", ".join([f"{col} = VALUES({col})" for col in update_columns])

    sql = f"""
        INSERT INTO destinations ({column_sql})
        VALUES ({placeholders})
        ON DUPLICATE KEY UPDATE
          {update_sql}
    """

    cursor.execute(sql, [values[col] for col in columns])

    cursor.execute(
        "SELECT id FROM destinations WHERE rag_place_id = %s LIMIT 1",
        (place_id,),
    )
    row = cursor.fetchone()
    if not row:
        raise RuntimeError(f"Could not fetch destination id for {place_id}")

    return int(row[0])


def build_rag_place_values(item: Dict[str, Any], destination_id: int) -> Dict[str, Any]:
    return {
        "place_id": as_text(item.get("place_id")),
        "destination_id": destination_id,
        "name": as_text(item.get("name")) or "",
        "aliases_json": as_json_text(item.get("aliases_json")),
        "province": as_text(item.get("province")),
        "city": as_text(item.get("city")),
        "area": as_text(item.get("area")),
        "destination_group": as_text(item.get("destination_group")),
        "address": as_text(item.get("address")),
        "latitude": as_float(item.get("latitude")),
        "longitude": as_float(item.get("longitude")),
        "category_main": as_text(item.get("category_main")),
        "category_sub": as_text(item.get("category_sub")),
        "category_main_norm": as_text(item.get("category_main_norm")),
        "category_sub_norm": as_text(item.get("category_sub_norm")),
        "tags_json": as_json_text(item.get("tags_json")),
        "interest_tags_json": as_json_text(item.get("interest_tags_json")),
        "suitable_for_json": as_json_text(item.get("suitable_for_json")),
        "avoid_for_json": as_json_text(item.get("avoid_for_json")),
        "description": as_text(item.get("description")),
        "short_description": as_text(item.get("short_description")),
        "open_time": as_text(item.get("open_time")),
        "close_time": as_text(item.get("close_time")),
        "best_time_of_day_json": as_json_text(item.get("best_time_of_day_json")),
        "suggested_slot": as_text(item.get("suggested_slot")),
        "slot_norm": as_text(item.get("slot_norm")),
        "duration_minutes": as_int(item.get("duration_minutes")),
        "is_night_activity": as_bool_int(item.get("is_night_activity")),
        "is_free": as_bool_int(item.get("is_free")),
        "entry_fee_min": as_float(item.get("entry_fee_min")),
        "entry_fee_max": as_float(item.get("entry_fee_max")),
        "budget_level": as_text(item.get("budget_level")),
        "budget_level_norm": as_text(item.get("budget_level_norm")),
        "price_note": as_text(item.get("price_note")),
        "walking_level": as_text(item.get("walking_level")),
        "walking_level_norm": as_text(item.get("walking_level_norm")),
        "activity_level": as_text(item.get("activity_level")),
        "activity_level_norm": as_text(item.get("activity_level_norm")),
        "elderly_friendly": as_text(item.get("elderly_friendly")),
        "elderly_friendly_norm": as_bool_int(item.get("elderly_friendly_norm")),
        "kid_friendly": as_text(item.get("kid_friendly")),
        "kid_friendly_norm": as_bool_int(item.get("kid_friendly_norm")),
        "nearby_area_json": as_json_text(item.get("nearby_area_json")),
        "transport_suggestion_json": as_json_text(item.get("transport_suggestion_json")),
        "quality_score": as_float(item.get("quality_score")),
        "recommended_use": as_text(item.get("recommended_use")),
        "recommended_use_norm": as_text(item.get("recommended_use_norm")),
        "is_generic": as_bool_int(item.get("is_generic")),
        "must_not_schedule_as_main": as_bool_int(item.get("must_not_schedule_as_main")),
        "requires_realtime_check": as_bool_int(item.get("requires_realtime_check")),
        "realtime_fields_json": as_json_text(item.get("realtime_fields_json")),
        "source": as_text(item.get("source")),
        "source_url": as_text(item.get("source_url")),
        "last_updated": as_text(item.get("last_updated")),
        "is_active": as_bool_int(item.get("is_active"), default=1),
        "search_text": as_text(item.get("search_text")),
        "raw_json": as_raw_json_text(item),
    }


def upsert_rag_place(cursor, item: Dict[str, Any], destination_id: int) -> None:
    values = build_rag_place_values(item, destination_id)

    missing = [col for col in RAG_PLACE_COLUMNS if col not in values]
    if missing:
        raise RuntimeError(f"Internal script error. Missing rag columns: {missing}")

    columns = RAG_PLACE_COLUMNS
    placeholders = ", ".join(["%s"] * len(columns))
    column_sql = ", ".join(columns)
    update_columns = [col for col in columns if col != "place_id"]
    update_sql = ", ".join([f"{col} = VALUES({col})" for col in update_columns])

    sql = f"""
        INSERT INTO rag_places ({column_sql})
        VALUES ({placeholders})
        ON DUPLICATE KEY UPDATE
          {update_sql}
    """

    cursor.execute(sql, [values[col] for col in columns])


def write_category_report(path: Path, places: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for item in places:
        rows.append(
            {
                "place_id": as_text(item.get("place_id")) or "",
                "name": as_text(item.get("name")) or "",
                "province": as_text(item.get("province")) or "",
                "category_main": as_text(item.get("category_main")) or "",
                "category_sub": as_text(item.get("category_sub")) or "",
                "app_category": normalize_app_category(item),
            }
        )

    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["place_id", "name", "province", "category_main", "category_sub", "app_category"],
        )
        writer.writeheader()
        writer.writerows(rows)


def print_category_summary(places: List[Dict[str, Any]]) -> None:
    counter = Counter(normalize_app_category(item) for item in places)
    print("")
    print("App category preview from input data:")
    for category in sorted(counter):
        print(f"  - {category}: {counter[category]}")

    unexpected = sorted(set(counter) - CANONICAL_APP_CATEGORIES)
    if unexpected:
        raise RuntimeError(f"Unexpected app categories generated: {unexpected}")


def import_places(args: argparse.Namespace) -> None:
    project_root = get_project_root()
    load_dotenv_if_exists(project_root)

    input_path = Path(args.input_file)
    if not input_path.is_absolute():
        input_path = project_root / input_path

    places = read_json_array(input_path)
    print_category_summary(places)

    if args.category_report_output:
        report_path = Path(args.category_report_output)
        if not report_path.is_absolute():
            report_path = project_root / report_path
        write_category_report(report_path, places)
        print(f"Category report written: {report_path}")

    if args.dry_run:
        print("Dry run enabled. No database changes were made.")
        return

    conn = connect_mysql(args)
    cursor = conn.cursor()

    imported = 0
    skipped = 0
    errors: List[Tuple[Optional[str], str]] = []

    try:
        for idx, item in enumerate(places, start=1):
            place_id = as_text(item.get("place_id"))

            if not place_id:
                skipped += 1
                errors.append((None, f"Row {idx}: missing place_id"))
                continue

            try:
                destination_id = upsert_destination(cursor, item)
                upsert_rag_place(cursor, item, destination_id)
                imported += 1

                if imported % args.commit_every == 0:
                    conn.commit()
                    print(f"Committed {imported} rows...")

            except Exception as exc:
                skipped += 1
                errors.append((place_id, str(exc)))
                if args.stop_on_error:
                    raise

        conn.commit()

    finally:
        cursor.close()
        conn.close()

    print("")
    print("Import finished.")
    print(f"Input file : {input_path}")
    print(f"Imported   : {imported}")
    print(f"Skipped    : {skipped}")

    if errors:
        print("")
        print("Errors / skipped rows:")
        for place_id, message in errors[:20]:
            print(f"  - {place_id or 'UNKNOWN'}: {message}")

        if len(errors) > 20:
            print(f"  ... and {len(errors) - 20} more")


def parse_args() -> argparse.Namespace:
    project_root = get_project_root()
    load_dotenv_if_exists(project_root)

    parser = argparse.ArgumentParser(
        description="Import reviewed places into UnuTrip MySQL schema v2."
    )

    parser.add_argument(
        "--input-file",
        default="data/processed/places_app_reviewed.json",
        help="Path to places_app_reviewed.json. Relative paths are resolved from smarttravel-rag-v2 root.",
    )

    parser.add_argument("--db-host", default=os.getenv("DB_HOST", DEFAULT_DB_HOST))
    parser.add_argument("--db-port", type=int, default=int(os.getenv("DB_PORT", DEFAULT_DB_PORT)))
    parser.add_argument("--db-user", default=os.getenv("DB_USER", DEFAULT_DB_USER))
    parser.add_argument("--db-password", default=os.getenv("DB_PASSWORD", DEFAULT_DB_PASSWORD))
    parser.add_argument("--db-name", default=os.getenv("DB_NAME", DEFAULT_DB_NAME))

    parser.add_argument(
        "--commit-every",
        type=int,
        default=500,
        help="Commit every N imported rows.",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only preview category mapping/report. Do not connect to MySQL or write database rows.",
    )

    parser.add_argument(
        "--category-report-output",
        default="data/processed/category_import_preview.csv",
        help="CSV report showing category_main/category_sub -> destinations.category before import. Relative paths are resolved from project root.",
    )

    parser.add_argument(
        "--stop-on-error",
        action="store_true",
        help="Stop immediately on first row error.",
    )

    return parser.parse_args()


if __name__ == "__main__":
    import_places(parse_args())
