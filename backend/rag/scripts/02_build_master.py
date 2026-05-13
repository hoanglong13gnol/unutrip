import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from core.config import settings
from rag.normalizer import normalize_dataframe


def main() -> None:
    settings.processed_data_dir.mkdir(parents=True, exist_ok=True)
    settings.reports_dir.mkdir(parents=True, exist_ok=True)

    if not settings.dataset_file.exists():
        raise FileNotFoundError(f"Dataset not found: {settings.dataset_file}")

    df = pd.read_excel(settings.dataset_file, sheet_name=settings.dataset_sheet)
    print("Loaded raw dataset:", df.shape)

    if "place_id" not in df.columns:
        raise ValueError("Missing required column: place_id")

    before = len(df)
    df = df.dropna(subset=["place_id"]).copy()
    df["place_id"] = df["place_id"].astype(str).str.strip()
    df = df.drop_duplicates(subset=["place_id"], keep="first").copy()
    after = len(df)

    print(f"Dedup place_id: {before} -> {after}")

    master = normalize_dataframe(df)

    master.to_parquet(settings.places_master_file, index=False)

    report = {
        "input_rows": int(before),
        "output_rows": int(len(master)),
        "unique_place_id": int(master["place_id"].nunique()),
        "columns": list(master.columns),
        "new_columns": [
            col for col in master.columns
            if col not in df.columns
        ],
        "null_counts_top": master.isna().sum().sort_values(ascending=False).head(80).astype(int).to_dict(),
        "budget_level_norm": master["budget_level_norm"].value_counts(dropna=False).astype(int).to_dict()
        if "budget_level_norm" in master.columns else {},
        "walking_level_norm": master["walking_level_norm"].value_counts(dropna=False).astype(int).to_dict()
        if "walking_level_norm" in master.columns else {},
        "activity_level_norm": master["activity_level_norm"].value_counts(dropna=False).astype(int).to_dict()
        if "activity_level_norm" in master.columns else {},
        "slot_norm": master["slot_norm"].value_counts(dropna=False).astype(int).to_dict()
        if "slot_norm" in master.columns else {},
        "recommended_use_norm": master["recommended_use_norm"].value_counts(dropna=False).astype(int).to_dict()
        if "recommended_use_norm" in master.columns else {},
        "category_main_norm_top": master["category_main_norm"].value_counts(dropna=False).head(50).astype(int).to_dict()
        if "category_main_norm" in master.columns else {},
        "is_active": master["is_active"].value_counts(dropna=False).astype(int).to_dict()
        if "is_active" in master.columns else {},
    }

    report_path = settings.reports_dir / "build_master_report.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Saved master: {settings.places_master_file}")
    print(f"Saved report: {report_path}")
    print("Master shape:", master.shape)


if __name__ == "__main__":
    main()