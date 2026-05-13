import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from core.config import settings


def main() -> None:
    df = pd.read_parquet(settings.places_master_file)

    cols = ["province", "province_norm"]
    result = (
        df[cols]
        .drop_duplicates()
        .sort_values(["province_norm", "province"])
    )

    print("Province count:", result["province_norm"].nunique())
    print(result.to_string(index=False))

    output_path = settings.reports_dir / "province_norm_values.csv"
    result.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"\nSaved: {output_path}")


if __name__ == "__main__":
    main()