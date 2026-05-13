import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from core.config import settings


ITINERARY_COLUMNS = [
    "place_id",
    "name",
    "province",
    "province_norm",
    "city",
    "city_norm",
    "area",
    "area_norm",
    "destination_group",
    "address",
    "latitude",
    "longitude",

    "category_main",
    "category_sub",
    "category_main_norm",
    "category_sub_norm",

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

    "walking_level",
    "walking_level_norm",
    "activity_level",
    "activity_level_norm",

    "elderly_friendly",
    "elderly_friendly_norm",
    "kid_friendly",
    "kid_friendly_norm",

    "suitable_for_json",
    "avoid_for_json",

    "distance_from_center_km",
    "nearby_area_json",
    "transport_suggestion_json",

    "quality_score",
    "recommended_use",
    "recommended_use_norm",
    "is_generic",
    "must_not_schedule_as_main",

    "requires_realtime_check",
    "realtime_fields_json",
    "is_active",
]


def clean_value(value):
    if pd.isna(value):
        return None

    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass

    return value


def infer_itinerary_role(row: pd.Series) -> str:
    category = str(row.get("category_main_norm") or "")
    sub = str(row.get("category_sub_norm") or "")
    slot = str(row.get("slot_norm") or "")
    recommended = str(row.get("recommended_use_norm") or "")

    text = f"{category} {sub}"

    if "food" in text or "am_thuc" in text or "nha_hang" in text or "cafe" in text:
        return "food_stop"

    if "shopping" in text or "market" in text or "cho" in text or "mua_sam" in text:
        return "shopping_stop"

    if slot in {"evening", "night"} or bool(row.get("is_night_activity")):
        return "night_activity"

    if recommended == "main":
        return "main_attraction"

    if recommended == "supporting":
        return "secondary_stop"

    if recommended == "optional":
        return "optional"

    if "park" in text or "cong_vien" in text:
        return "rest_stop"

    return "secondary_stop"


def infer_sequence_priority(row: pd.Series) -> int:
    slot = str(row.get("slot_norm") or "")
    role = str(row.get("itinerary_role") or "")

    if slot == "morning":
        return 1
    if slot == "noon" or role == "food_stop":
        return 2
    if slot == "afternoon":
        return 3
    if slot in {"evening", "night"} or role == "night_activity":
        return 4
    if slot == "full_day":
        return 1

    return 3


def can_visit_slot(row: pd.Series, target: str) -> bool:
    slot = str(row.get("slot_norm") or "")
    if slot in {"any", "full_day"}:
        return True

    if target == "morning":
        return slot in {"morning"}
    if target == "afternoon":
        return slot in {"afternoon"}
    if target == "evening":
        return slot in {"evening", "night"}
    if target == "night":
        return slot in {"night", "evening"}

    return False


def compute_itinerary_weight(row: pd.Series) -> float:
    score = 0.0

    quality = row.get("quality_score")
    if pd.notna(quality):
        score += float(quality) * 10.0

    recommended = row.get("recommended_use_norm")
    if recommended == "main":
        score += 15
    elif recommended == "supporting":
        score += 8
    elif recommended == "optional":
        score += 3

    if row.get("must_not_schedule_as_main") is True:
        score -= 25

    if row.get("requires_realtime_check") is True:
        score -= 3

    walking = row.get("walking_level_norm")
    if walking == "easy":
        score += 5
    elif walking == "moderate":
        score += 2
    elif walking == "hard":
        score -= 5

    if row.get("kid_friendly_norm") is True:
        score += 3

    if row.get("elderly_friendly_norm") is True:
        score += 3

    return round(score, 3)


def main() -> None:
    if not settings.places_master_file.exists():
        raise FileNotFoundError(
            f"Master file not found: {settings.places_master_file}. "
            "Run scripts\\02_build_master.py first."
        )

    df = pd.read_parquet(settings.places_master_file)

    if "is_active" in df.columns:
        df = df[df["is_active"] == True].copy()

    available_columns = [col for col in ITINERARY_COLUMNS if col in df.columns]
    itinerary_df = df[available_columns].copy()

    itinerary_df["itinerary_role"] = itinerary_df.apply(infer_itinerary_role, axis=1)
    itinerary_df["sequence_priority"] = itinerary_df.apply(infer_sequence_priority, axis=1)

    itinerary_df["can_visit_morning"] = itinerary_df.apply(
        lambda row: can_visit_slot(row, "morning"), axis=1
    )
    itinerary_df["can_visit_afternoon"] = itinerary_df.apply(
        lambda row: can_visit_slot(row, "afternoon"), axis=1
    )
    itinerary_df["can_visit_evening"] = itinerary_df.apply(
        lambda row: can_visit_slot(row, "evening"), axis=1
    )
    itinerary_df["can_visit_night"] = itinerary_df.apply(
        lambda row: can_visit_slot(row, "night"), axis=1
    )

    itinerary_df["itinerary_weight"] = itinerary_df.apply(compute_itinerary_weight, axis=1)

    itinerary_df = itinerary_df.sort_values(
        by=["province", "sequence_priority", "itinerary_weight", "name"],
        ascending=[True, True, False, True],
        na_position="last",
    )

    records = []
    for row in itinerary_df.to_dict(orient="records"):
        records.append({key: clean_value(value) for key, value in row.items()})

    settings.places_itinerary_file.write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    report = {
        "output_file": str(settings.places_itinerary_file),
        "row_count": len(records),
        "column_count": len(itinerary_df.columns),
        "columns": list(itinerary_df.columns),
        "province_count": int(itinerary_df["province"].nunique()) if "province" in itinerary_df.columns else None,
        "itinerary_role_counts": itinerary_df["itinerary_role"].value_counts(dropna=False).astype(int).to_dict(),
        "sequence_priority_counts": itinerary_df["sequence_priority"].value_counts(dropna=False).astype(int).to_dict(),
        "can_visit_morning_count": int(itinerary_df["can_visit_morning"].sum()),
        "can_visit_afternoon_count": int(itinerary_df["can_visit_afternoon"].sum()),
        "can_visit_evening_count": int(itinerary_df["can_visit_evening"].sum()),
        "can_visit_night_count": int(itinerary_df["can_visit_night"].sum()),
        "sample_records": records[:3],
    }

    report_path = settings.reports_dir / "export_itinerary_dataset_report.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Saved itinerary dataset: {settings.places_itinerary_file}")
    print(f"Saved report: {report_path}")
    print(f"Rows: {len(records)}")
    print(f"Columns: {len(itinerary_df.columns)}")


if __name__ == "__main__":
    main()
