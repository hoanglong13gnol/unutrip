import json
import re
import unicodedata
from typing import Any

import pandas as pd


TRUE_VALUES = {
    "true", "1", "yes", "y", "co", "có", "ok", "active", "hoat dong", "hoạt động"
}

FALSE_VALUES = {
    "false", "0", "no", "n", "khong", "không", "inactive", "none", "null", ""
}


def strip_text(value: Any) -> str | None:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    if text == "" or text.lower() in {"nan", "none", "null"}:
        return None
    return text


def remove_accents(text: str) -> str:
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.replace("đ", "d").replace("Đ", "D")
    return text


def normalize_key(value: Any) -> str | None:
    text = strip_text(value)
    if text is None:
        return None
    text = remove_accents(text).lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text or None


def to_bool(value: Any, default: bool | None = None) -> bool | None:
    if value is None or pd.isna(value):
        return default

    if isinstance(value, bool):
        return value

    if isinstance(value, (int, float)) and not pd.isna(value):
        if value == 1:
            return True
        if value == 0:
            return False

    text = remove_accents(str(value).strip().lower())

    if text in TRUE_VALUES:
        return True
    if text in FALSE_VALUES:
        return False

    return default


def to_number(value: Any, default: float | None = None) -> float | None:
    if value is None or pd.isna(value):
        return default
    try:
        return float(value)
    except Exception:
        return default


def to_int(value: Any, default: int | None = None) -> int | None:
    number = to_number(value)
    if number is None:
        return default
    try:
        return int(round(number))
    except Exception:
        return default


def parse_json_like(value: Any) -> list[Any] | dict[str, Any] | None:
    text = strip_text(value)
    if text is None:
        return None

    try:
        parsed = json.loads(text)
        return parsed
    except Exception:
        pass

    # fallback: split comma/semicolon text into list
    if "," in text or ";" in text:
        parts = re.split(r"[,;]", text)
        parts = [p.strip() for p in parts if p.strip()]
        return parts or None

    return [text]


def json_to_text(value: Any) -> str:
    parsed = parse_json_like(value)
    if parsed is None:
        return ""

    if isinstance(parsed, list):
        return ", ".join(str(x) for x in parsed if str(x).strip())

    if isinstance(parsed, dict):
        chunks = []
        for key, val in parsed.items():
            if isinstance(val, list):
                chunks.append(f"{key}: {', '.join(str(x) for x in val)}")
            else:
                chunks.append(f"{key}: {val}")
        return "; ".join(chunks)

    return str(parsed)


def normalize_budget(value: Any, is_free: Any = None) -> str | None:
    if to_bool(is_free, default=False):
        return "free"

    key = normalize_key(value)
    if key is None:
        return None

    mapping = {
        "mien_phi": "free",
        "free": "free",
        "thap": "low",
        "low": "low",
        "gia_re": "low",
        "tiet_kiem": "low",
        "thap_trung_binh": "low_medium",
        "low_medium": "low_medium",
        "trung_binh": "medium",
        "medium": "medium",
        "vua": "medium",
        "trung_binh_cao": "medium_high",
        "medium_high": "medium_high",
        "cao": "high",
        "high": "high",
        "luxury": "luxury",
        "sang_trong": "luxury",
    }
    return mapping.get(key, key)


def normalize_walking(value: Any) -> str | None:
    key = normalize_key(value)
    if key is None:
        return None

    mapping = {
        "1": "easy",
        "de": "easy",
        "thap": "easy",
        "nhe": "easy",
        "low": "easy",
        "easy": "easy",
        "2": "moderate",
        "trung_binh": "moderate",
        "vua": "moderate",
        "medium": "moderate",
        "moderate": "moderate",
        "3": "hard",
        "kho": "hard",
        "cao": "hard",
        "high": "hard",
        "hard": "hard",
        "nang": "hard",
    }
    return mapping.get(key, key)


def normalize_activity(value: Any) -> str | None:
    key = normalize_key(value)
    if key is None:
        return None

    mapping = {
        "nhe": "light",
        "thap": "light",
        "low": "light",
        "easy": "light",
        "light": "light",
        "vua": "moderate",
        "trung_binh": "moderate",
        "medium": "moderate",
        "moderate": "moderate",
        "vua_cao": "active",
        "active": "active",
        "cao": "active",
        "high": "active",
        "nang": "active",
        "hard": "active",
    }
    return mapping.get(key, key)


def normalize_slot(value: Any) -> str | None:
    key = normalize_key(value)
    if key is None:
        return None

    mapping = {
        "sang": "morning",
        "morning": "morning",
        "trua": "noon",
        "noon": "noon",
        "chieu": "afternoon",
        "afternoon": "afternoon",
        "toi": "evening",
        "buoi_toi": "evening",
        "evening": "evening",
        "dem": "night",
        "night": "night",
        "ca_ngay": "full_day",
        "full_day": "full_day",
        "any": "any",
        "bat_ky": "any",
    }
    return mapping.get(key, key)


def normalize_recommended_use(value: Any) -> str | None:
    key = normalize_key(value)
    if key is None:
        return None

    mapping = {
        "main": "main",
        "diem_chinh": "main",
        "primary": "main",
        "supporting": "supporting",
        "phu": "supporting",
        "secondary": "supporting",
        "optional": "optional",
        "tuy_chon": "optional",
        "rag_ready": "rag_ready",
    }
    return mapping.get(key, key)


def normalize_category(value: Any) -> str | None:
    key = normalize_key(value)
    if key is None:
        return None

    mapping = {
        "bien": "beach",
        "dao": "island",
        "nui": "mountain",
        "thac": "waterfall",
        "ho": "lake",
        "song": "river",
        "chua": "temple",
        "den": "temple",
        "tam_linh": "spiritual",
        "bao_tang": "museum",
        "lich_su": "history",
        "van_hoa": "culture",
        "pho_co": "old_town",
        "cho": "market",
        "am_thuc": "food",
        "nha_hang": "food",
        "cafe": "cafe",
        "cong_vien": "park",
        "khu_vui_choi": "entertainment",
        "mua_sam": "shopping",
        "check_in": "checkin",
        "tham_quan": "sightseeing",
        "du_lich_sinh_thai": "eco_tourism",
    }
    return mapping.get(key, key)


def build_search_text(row: pd.Series) -> str:
    parts = [
        strip_text(row.get("name")),
        json_to_text(row.get("aliases_json")),
        strip_text(row.get("province")),
        strip_text(row.get("city")),
        strip_text(row.get("area")),
        strip_text(row.get("destination_group")),
        strip_text(row.get("category_main")),
        strip_text(row.get("category_sub")),
        json_to_text(row.get("tags_json")),
        json_to_text(row.get("interest_tags_json")),
        strip_text(row.get("short_description")),
        strip_text(row.get("description")),
        json_to_text(row.get("suitable_for_json")),
        json_to_text(row.get("avoid_for_json")),
    ]
    return " | ".join([p for p in parts if p])


def normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    # basic text cleanup
    for col in out.columns:
        if out[col].dtype == "object":
            out[col] = out[col].apply(strip_text)

    # numeric fields
    for col in [
        "latitude",
        "longitude",
        "entry_fee_min",
        "entry_fee_max",
        "distance_from_center_km",
        "quality_score",
    ]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")

    if "duration_minutes" in out.columns:
        out["duration_minutes"] = pd.to_numeric(out["duration_minutes"], errors="coerce").round().astype("Int64")

    # booleans
    bool_cols = [
        "is_night_activity",
        "is_free",
        "is_generic",
        "must_not_schedule_as_main",
        "requires_realtime_check",
        "is_active",
    ]
    for col in bool_cols:
        if col in out.columns:
            out[col] = out[col].apply(lambda x: to_bool(x, default=False))

    if "kid_friendly" in out.columns:
        out["kid_friendly_norm"] = out["kid_friendly"].apply(lambda x: to_bool(x, default=None))

    if "elderly_friendly" in out.columns:
        out["elderly_friendly_norm"] = out["elderly_friendly"].apply(lambda x: to_bool(x, default=None))

    if "budget_level" in out.columns:
        out["budget_level_norm"] = out.apply(
            lambda row: normalize_budget(row.get("budget_level"), row.get("is_free")),
            axis=1,
        )

    if "walking_level" in out.columns:
        out["walking_level_norm"] = out["walking_level"].apply(normalize_walking)

    if "activity_level" in out.columns:
        out["activity_level_norm"] = out["activity_level"].apply(normalize_activity)

    if "suggested_slot" in out.columns:
        out["slot_norm"] = out["suggested_slot"].apply(normalize_slot)

    if "recommended_use" in out.columns:
        out["recommended_use_norm"] = out["recommended_use"].apply(normalize_recommended_use)

    if "category_main" in out.columns:
        out["category_main_norm"] = out["category_main"].apply(normalize_category)

    if "category_sub" in out.columns:
        out["category_sub_norm"] = out["category_sub"].apply(normalize_category)

    out["province_norm"] = out["province"].apply(normalize_key) if "province" in out.columns else None
    out["city_norm"] = out["city"].apply(normalize_key) if "city" in out.columns else None
    out["area_norm"] = out["area"].apply(normalize_key) if "area" in out.columns else None
    out["name_norm"] = out["name"].apply(normalize_key) if "name" in out.columns else None

    out["search_text"] = out.apply(build_search_text, axis=1)

    # default active if missing
    if "is_active" in out.columns:
        out["is_active"] = out["is_active"].fillna(True).astype(bool)

    return out