import csv
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from core.config import settings
from rag.text_utils import normalize_text


def load_places() -> list[dict[str, Any]]:
    data = json.loads(settings.places_app_file.read_text(encoding="utf-8"))

    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        return data.get("places", [])

    return []


def text_blob(place: dict[str, Any]) -> str:
    # Chỉ dùng field tín hiệu mạnh, không dùng search_text/description quá rộng.
    fields = [
        "name",
        "aliases_json",
        "category_main",
        "category_sub",
        "tags_json",
        "interest_tags_json",
        "destination_group",
    ]

    return normalize_text(
        " ".join(str(place.get(field) or "") for field in fields)
    )


def contains_any_token(blob: str, terms: list[str]) -> bool:
    padded = f" {blob} "
    return any(term in padded for term in terms)


def add_issue(
    issues: list[dict[str, Any]],
    place: dict[str, Any],
    issue_type: str,
    severity: str,
    message: str,
) -> None:
    issues.append({
        "issue_type": issue_type,
        "severity": severity,
        "place_id": place.get("place_id"),
        "name": place.get("name"),
        "province": place.get("province"),
        "area": place.get("area"),
        "category_main": place.get("category_main"),
        "category_sub": place.get("category_sub"),
        "quality_score": place.get("quality_score"),
        "recommended_use": place.get("recommended_use"),
        "message": message,
    })


def scan_category_mismatch(place: dict[str, Any], issues: list[dict[str, Any]]) -> None:
    blob = text_blob(place)
    category_main_norm = normalize_text(str(place.get("category_main") or ""))
    category_sub_norm = normalize_text(str(place.get("category_sub") or ""))

    category_blob = f" {category_main_norm} {category_sub_norm} "

    beach_terms = [
        " bai bien ",
        " bien ",
        " beach ",
        " vinh ",
        " dao ",
        " hon ",
        " dam pha ",
        " lang co ",
        " doc let ",
        " van phong ",
        " diep son ",
    ]

    spiritual_terms = [
        " chua ",
        " den ",
        " dinh ",
        " mieu ",
        " lang mo ",
        " lang tam ",
        " nha tho ",
        " tam linh ",
        " thanh that ",
    ]

    nature_terms = [
        " suoi ",
        " thac ",
        " nui ",
        " rung ",
        " ho ",
        " vuon quoc gia ",
        " sinh thai ",
        " hang ",
        " dong ",
    ]

    has_beach_signal = contains_any_token(blob, beach_terms)
    has_spiritual_signal = contains_any_token(blob, spiritual_terms)
    has_nature_signal = contains_any_token(blob, nature_terms)

    is_nature_category = contains_any_token(
        category_blob,
        [
            " thien nhien ",
            " bien ",
            " sinh thai ",
            " lake ",
            " beach ",
        ],
    )
    is_spiritual_category = contains_any_token(
        category_blob,
        [
            " tam linh ",
            " chua ",
            " den ",
            " dinh ",
            " mieu ",
            " nha tho ",
        ],
    )
    is_culture_category = contains_any_token(
        category_blob,
        [
            " van hoa ",
            " di tich ",
            " lich su ",
            " bao tang ",
        ],
    )

    if has_beach_signal and not is_nature_category:
        add_issue(
            issues,
            place,
            "category_mismatch_beach",
            "high",
            "Có tín hiệu biển/bãi biển/vịnh/đảo nhưng category không phải Thiên nhiên/Biển.",
        )

    if has_spiritual_signal and not is_spiritual_category and not is_culture_category:
        add_issue(
            issues,
            place,
            "category_mismatch_spiritual",
            "medium",
            "Có tín hiệu tâm linh nhưng category không thuộc Tâm linh/Văn hóa/Di tích.",
        )

    if has_nature_signal and not has_beach_signal and not is_nature_category:
        add_issue(
            issues,
            place,
            "category_mismatch_nature",
            "medium",
            "Có tín hiệu thiên nhiên như suối/thác/núi/rừng/hồ nhưng category không phải Thiên nhiên.",
        )


def scan_fee(place: dict[str, Any], issues: list[dict[str, Any]]) -> None:
    fee_min = place.get("entry_fee_min")
    fee_max = place.get("entry_fee_max")

    try:
        if fee_min is not None and fee_max is not None:
            fee_min_value = float(fee_min)
            fee_max_value = float(fee_max)

            if fee_min_value < 0 or fee_max_value < 0:
                add_issue(
                    issues,
                    place,
                    "invalid_fee_negative",
                    "high",
                    "Phí vào cửa âm.",
                )

            if fee_min_value > fee_max_value:
                add_issue(
                    issues,
                    place,
                    "invalid_fee_range",
                    "high",
                    "entry_fee_min lớn hơn entry_fee_max.",
                )
    except Exception:
        add_issue(
            issues,
            place,
            "invalid_fee_type",
            "medium",
            "Phí vào cửa không parse được thành số.",
        )


def scan_coordinates(place: dict[str, Any], issues: list[dict[str, Any]]) -> None:
    lat = place.get("latitude")
    lon = place.get("longitude")

    if lat in [None, ""] or lon in [None, ""]:
        add_issue(
            issues,
            place,
            "missing_coordinates",
            "medium",
            "Thiếu latitude/longitude.",
        )
        return

    try:
        lat_value = float(lat)
        lon_value = float(lon)

        if not (8.0 <= lat_value <= 24.5 and 102.0 <= lon_value <= 110.5):
            add_issue(
                issues,
                place,
                "coordinate_out_of_vietnam_range",
                "medium",
                "Tọa độ nằm ngoài khoảng Việt Nam dự kiến.",
            )
    except Exception:
        add_issue(
            issues,
            place,
            "invalid_coordinates_type",
            "medium",
            "Latitude/longitude không parse được thành số.",
        )


def scan_time(place: dict[str, Any], issues: list[dict[str, Any]]) -> None:
    open_time = str(place.get("open_time") or "").strip()
    close_time = str(place.get("close_time") or "").strip()

    if not open_time or not close_time:
        return

    def valid_hhmm(value: str) -> bool:
        parts = value.split(":")
        if len(parts) != 2:
            return False

        try:
            hour = int(parts[0])
            minute = int(parts[1])
            return 0 <= hour <= 23 and 0 <= minute <= 59
        except Exception:
            return False

    if not valid_hhmm(open_time) or not valid_hhmm(close_time):
        add_issue(
            issues,
            place,
            "invalid_open_close_time",
            "low",
            "open_time/close_time không đúng định dạng HH:MM.",
        )


def scan_duplicate_names(places: list[dict[str, Any]], issues: list[dict[str, Any]]) -> None:
    groups: dict[str, list[dict[str, Any]]] = {}

    remove_words = [
        "khu du lich",
        "bai bien",
        "bai tam",
        "diem du lich",
        "khu",
        "dia diem",
    ]

    for place in places:
        name = normalize_text(str(place.get("name") or ""))

        for word in remove_words:
            name = name.replace(word, " ")

        key = " ".join(name.split())

        if not key:
            continue

        groups.setdefault(key, []).append(place)

    for key, group in groups.items():
        if len(group) <= 1:
            continue

        ids = [str(item.get("place_id")) for item in group]
        names = [str(item.get("name")) for item in group]

        for place in group:
            add_issue(
                issues,
                place,
                "possible_duplicate_name",
                "low",
                f"Có thể trùng tên/near-duplicate. Group key={key}. IDs={ids}. Names={names}",
            )


def main() -> None:
    places = load_places()
    issues: list[dict[str, Any]] = []

    for place in places:
        scan_category_mismatch(place, issues)
        scan_fee(place, issues)
        scan_coordinates(place, issues)
        scan_time(place, issues)

    scan_duplicate_names(places, issues)

    settings.reports_dir.mkdir(parents=True, exist_ok=True)

    json_path = settings.reports_dir / "data_quality_issues.json"
    csv_path = settings.reports_dir / "data_quality_issues.csv"

    json_path.write_text(
        json.dumps(
            {
                "place_count": len(places),
                "issue_count": len(issues),
                "issues": issues,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    fieldnames = [
        "issue_type",
        "severity",
        "place_id",
        "name",
        "province",
        "area",
        "category_main",
        "category_sub",
        "quality_score",
        "recommended_use",
        "message",
    ]

    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(issues)

    issue_counts: dict[str, int] = {}
    severity_counts: dict[str, int] = {}

    for issue in issues:
        issue_type = issue["issue_type"]
        severity = issue["severity"]

        issue_counts[issue_type] = issue_counts.get(issue_type, 0) + 1
        severity_counts[severity] = severity_counts.get(severity, 0) + 1

    print(f"Places: {len(places)}")
    print(f"Issues: {len(issues)}")
    print("Issue counts:")
    for key, value in sorted(issue_counts.items()):
        print(f"- {key}: {value}")

    print("Severity counts:")
    for key, value in sorted(severity_counts.items()):
        print(f"- {key}: {value}")

    print(f"Saved JSON: {json_path}")
    print(f"Saved CSV: {csv_path}")


if __name__ == "__main__":
    main()