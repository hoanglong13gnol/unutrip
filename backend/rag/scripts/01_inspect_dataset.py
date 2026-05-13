import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from core.config import settings


def value_counts_safe(df: pd.DataFrame, column: str, limit: int = 50) -> dict:
    if column not in df.columns:
        return {}
    return (
        df[column]
        .fillna("__NULL__")
        .astype(str)
        .str.strip()
        .value_counts()
        .head(limit)
        .to_dict()
    )


def main() -> None:
    if not settings.dataset_file.exists():
        raise FileNotFoundError(f"Dataset not found: {settings.dataset_file}")

    settings.reports_dir.mkdir(parents=True, exist_ok=True)

    xls = pd.ExcelFile(settings.dataset_file)
    print("Sheets:")
    for sheet in xls.sheet_names:
        print(f"- {sheet}")

    if settings.dataset_sheet not in xls.sheet_names:
        raise ValueError(
            f"Sheet '{settings.dataset_sheet}' not found. "
            f"Available sheets: {xls.sheet_names}"
        )

    df = pd.read_excel(settings.dataset_file, sheet_name=settings.dataset_sheet)

    print("\nShape:", df.shape)
    print("\nColumns:")
    for col in df.columns:
        print(f"- {col}")

    report = {
        "dataset_file": str(settings.dataset_file),
        "sheet": settings.dataset_sheet,
        "row_count": int(len(df)),
        "column_count": int(len(df.columns)),
        "columns": list(df.columns),
        "place_id_unique": int(df["place_id"].nunique()) if "place_id" in df.columns else None,
        "place_id_null": int(df["place_id"].isna().sum()) if "place_id" in df.columns else None,
        "place_id_duplicate_count": int(df["place_id"].duplicated().sum()) if "place_id" in df.columns else None,
        "null_counts_top": df.isna().sum().sort_values(ascending=False).head(60).astype(int).to_dict(),
        "province_counts_top": value_counts_safe(df, "province", 80),
        "category_main_counts": value_counts_safe(df, "category_main", 80),
        "category_sub_counts": value_counts_safe(df, "category_sub", 80),
        "budget_level_values": value_counts_safe(df, "budget_level", 80),
        "walking_level_values": value_counts_safe(df, "walking_level", 80),
        "activity_level_values": value_counts_safe(df, "activity_level", 80),
        "kid_friendly_values": value_counts_safe(df, "kid_friendly", 80),
        "elderly_friendly_values": value_counts_safe(df, "elderly_friendly", 80),
        "suggested_slot_values": value_counts_safe(df, "suggested_slot", 80),
        "recommended_use_values": value_counts_safe(df, "recommended_use", 80),
        "requires_realtime_check_values": value_counts_safe(df, "requires_realtime_check", 80),
        "must_not_schedule_as_main_values": value_counts_safe(df, "must_not_schedule_as_main", 80),
    }

    if "quality_score" in df.columns:
        qs = pd.to_numeric(df["quality_score"], errors="coerce")
        report["quality_score"] = {
            "min": float(qs.min()) if qs.notna().any() else None,
            "max": float(qs.max()) if qs.notna().any() else None,
            "mean": float(qs.mean()) if qs.notna().any() else None,
            "null_count": int(qs.isna().sum()),
        }

    report_path = settings.reports_dir / "dataset_inspection_report.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"\nSaved report: {report_path}")


if __name__ == "__main__":
    main()
