import csv
import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from core.config import settings
from rag.text_utils import normalize_text


OUTPUT_FILE = settings.processed_data_dir / "places_app_autofixed.json"
REPORT_JSON = settings.reports_dir / "data_quality_autofix_report.json"
REPORT_CSV = settings.reports_dir / "data_quality_autofix_changes.csv"


def load_places() -> list[dict[str, Any]]:
    data = json.loads(settings.places_app_file.read_text(encoding="utf-8"))

    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        return data.get("places", [])

    return []


def safe_json_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]

    if not value:
        return []

    try:
        parsed = json.loads(str(value))
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
    except Exception:
        pass

    return [str(value)]


def name_alias_blob(place: dict[str, Any]) -> str:
    aliases = safe_json_list(place.get("aliases_json"))

    fields = [
        str(place.get("name") or ""),
        " ".join(aliases),
    ]

    return normalize_text(" ".join(fields))


def supporting_blob(place: dict[str, Any]) -> str:
    # Chỉ dùng tags để hỗ trợ, không dùng destination_group vì dễ gây nhiễu theo vùng.
    tags = safe_json_list(place.get("tags_json"))

    fields = [
        " ".join(tags),
        str(place.get("category_main") or ""),
        str(place.get("category_sub") or ""),
    ]

    return normalize_text(" ".join(fields))


def contains_any(blob: str, terms: list[str]) -> bool:
    padded = f" {blob} "
    return any(term in padded for term in terms)


def has_strong_beach_signal(place: dict[str, Any]) -> bool:
    name_blob = name_alias_blob(place)
    support_blob = supporting_blob(place)

    # Chỉ những từ này trong name/alias mới đủ mạnh để auto-fix.
    strong_name_terms = [
        " bai bien ",
        " beach ",
        " bien ",
        " vinh ",
        " dao ",
        " hon ",
        " dam pha ",
        " doc let ",
        " lang co ",
        " van phong ",
        " diep son ",
        " binh ba ",
        " binh hung ",
        " binh lap ",
        " nam du ",
        " phu quoc ",
        " con dao ",
    ]

    # Tags chỉ được dùng khi name/alias cũng có một tín hiệu địa hình/liên quan biển nhẹ.
    support_terms = [
        " bien ",
        " bai bien ",
        " beach ",
        " vinh ",
        " dao ",
        " hon ",
        " dam pha ",
        " nghi duong ",
        " hai san ",
    ]

    weak_name_terms = [
        " bai ",
        " vinh ",
        " dao ",
        " hon ",
        " cang ",
        " ben tau ",
        " lang chai ",
    ]

    if contains_any(name_blob, strong_name_terms):
        return True

    if contains_any(name_blob, weak_name_terms) and contains_any(support_blob, support_terms):
        return True

    return False


def is_already_beach_or_nature(place: dict[str, Any]) -> bool:
    category_blob = normalize_text(
        " ".join([
            str(place.get("category_main") or ""),
            str(place.get("category_sub") or ""),
            str(place.get("category_main_norm") or ""),
            str(place.get("category_sub_norm") or ""),
        ])
    )

    padded = f" {category_blob} "

    return any(
        term in padded
        for term in [
            " thien nhien ",
            " bien ",
            " sinh thai ",
            " nature ",
            " beach ",
        ]
    )


def is_obvious_non_beach(place: dict[str, Any]) -> bool:
    name_blob = name_alias_blob(place)

    non_beach_terms = [
        " nha tho ",
        " chua ",
        " den ",
        " dinh ",
        " mieu ",
        " thap ba ",
        " bao tang ",
        " quang truong ",
        " cho dem ",
        " cho ",
        " cap treo ",
        " khu pho ",
        " dinh bao dai ",
        " vien hai duong hoc ",
        " resort ",
        " tam bun ",
        " suoi khoang ",
        " san golf ",
        " lang nghe ",
        " lang yen ",
    ]

    return contains_any(name_blob, non_beach_terms)


def should_fix(place: dict[str, Any]) -> bool:
    if not place.get("is_active", True):
        return False

    if is_already_beach_or_nature(place):
        return False

    if is_obvious_non_beach(place):
        return False

    return has_strong_beach_signal(place)


def safe_append_tags(tags_raw: Any, new_tags: list[str]) -> str:
    parsed = safe_json_list(tags_raw)
    existing = {normalize_text(str(tag)) for tag in parsed}

    for tag in new_tags:
        if normalize_text(tag) not in existing:
            parsed.append(tag)

    return json.dumps(parsed, ensure_ascii=False)


def apply_fix(place: dict[str, Any]) -> dict[str, Any]:
    fixed = deepcopy(place)

    fixed["category_main"] = "Thiên nhiên"
    fixed["category_sub"] = "Biển đảo/rừng núi/sinh thái"
    fixed["category_main_norm"] = "nature"
    fixed["category_sub_norm"] = "bien_dao_rung_nui_sinh_thai"
    fixed["tags_json"] = safe_append_tags(fixed.get("tags_json"), ["biển", "thiên nhiên"])

    return fixed


def main() -> None:
    places = load_places()

    fixed_places = []
    changes = []

    for place in places:
        if should_fix(place):
            fixed = apply_fix(place)

            changes.append({
                "place_id": place.get("place_id"),
                "name": place.get("name"),
                "province": place.get("province"),
                "area": place.get("area"),
                "old_category_main": place.get("category_main"),
                "old_category_sub": place.get("category_sub"),
                "new_category_main": fixed.get("category_main"),
                "new_category_sub": fixed.get("category_sub"),
                "reason": "safe_name_alias_beach_signal_category_mismatch",
            })

            fixed_places.append(fixed)
        else:
            fixed_places.append(place)

    settings.processed_data_dir.mkdir(parents=True, exist_ok=True)
    settings.reports_dir.mkdir(parents=True, exist_ok=True)

    OUTPUT_FILE.write_text(
        json.dumps(fixed_places, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    REPORT_JSON.write_text(
        json.dumps(
            {
                "input_file": str(settings.places_app_file),
                "output_file": str(OUTPUT_FILE),
                "place_count": len(places),
                "changed_count": len(changes),
                "changes": changes,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    fieldnames = [
        "place_id",
        "name",
        "province",
        "area",
        "old_category_main",
        "old_category_sub",
        "new_category_main",
        "new_category_sub",
        "reason",
    ]

    with REPORT_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(changes)

    print(f"Places: {len(places)}")
    print(f"Changed: {len(changes)}")
    print(f"Saved fixed dataset: {OUTPUT_FILE}")
    print(f"Saved report JSON: {REPORT_JSON}")
    print(f"Saved report CSV: {REPORT_CSV}")


if __name__ == "__main__":
    main()