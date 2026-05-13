import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from core.config import settings


APP_COLUMNS = [
    "place_id",
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
    "source",
    "source_url",
    "last_updated",
    "is_active",
    "search_text",
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


def main() -> None:
    if not settings.places_master_file.exists():
        raise FileNotFoundError(
            f"Master file not found: {settings.places_master_file}. "
            "Run scripts\\02_build_master.py first."
        )

    df = pd.read_parquet(settings.places_master_file)

    if "is_active" in df.columns:
        df = df[df["is_active"] == True].copy()

    available_columns = [col for col in APP_COLUMNS if col in df.columns]
    app_df = df[available_columns].copy()

    app_df = app_df.sort_values(
        by=["province", "quality_score", "name"],
        ascending=[True, False, True],
        na_position="last",
    )

    records = []
    for row in app_df.to_dict(orient="records"):
        records.append({key: clean_value(value) for key, value in row.items()})

    settings.places_app_file.write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    report = {
        "output_file": str(settings.places_app_file),
        "row_count": len(records),
        "column_count": len(available_columns),
        "columns": available_columns,
        "province_count": int(app_df["province"].nunique()) if "province" in app_df.columns else None,
        "category_main_count": int(app_df["category_main"].nunique()) if "category_main" in app_df.columns else None,
        "sample_records": records[:3],
    }

    report_path = settings.reports_dir / "export_app_dataset_report.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Saved app dataset: {settings.places_app_file}")
    print(f"Saved report: {report_path}")
    print(f"Rows: {len(records)}")
    print(f"Columns: {len(available_columns)}")


if __name__ == "__main__":
    main()