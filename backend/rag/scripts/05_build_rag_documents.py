import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from core.config import settings
from rag.normalizer import json_to_text, strip_text
from rag.text_utils import normalize_text

def get_input_file() -> Path:
    reviewed_file = settings.processed_data_dir / "places_app_reviewed.json"

    if reviewed_file.exists():
        return reviewed_file

    if settings.places_app_file.exists():
        return settings.places_app_file

    raise FileNotFoundError(
        "No app dataset found. Expected places_app_reviewed.json or places_app.json."
    )


def load_places_dataframe() -> tuple[pd.DataFrame, Path]:
    input_file = get_input_file()
    data = json.loads(input_file.read_text(encoding="utf-8"))

    if isinstance(data, list):
        places = data
    elif isinstance(data, dict):
        places = data.get("places", [])
    else:
        places = []

    df = pd.DataFrame(places)

    if "is_active" in df.columns:
        df = df[df["is_active"] == True].copy()

    return df, input_file


def clean_value(value: Any):
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass

    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass

    return value


def text_join(parts: list[Any]) -> str:
    cleaned = []

    for part in parts:
        if part is None:
            continue

        text = str(part).strip()

        if not text or text.lower() in {"nan", "none", "null"}:
            continue

        cleaned.append(text)

    return "\n".join(cleaned)

def make_norm_key(value: Any) -> str | None:
    text = normalize_text(str(value or "")).strip()

    if not text:
        return None

    return text.replace(" ", "_")
def base_metadata(row: pd.Series) -> dict[str, Any]:
    keys = [
        "place_id",
        "name",
        "province",
        "province_norm",
        "city",
        "city_norm",
        "area",
        "area_norm",
        "destination_group",
        "latitude",
        "longitude",
        "category_main",
        "category_sub",
        "category_main_norm",
        "category_sub_norm",
        "slot_norm",
        "budget_level_norm",
        "walking_level_norm",
        "activity_level_norm",
        "kid_friendly_norm",
        "elderly_friendly_norm",
        "quality_score",
        "recommended_use_norm",
        "must_not_schedule_as_main",
        "requires_realtime_check",
        "is_active",
    ]

    meta = {}

    for key in keys:
        if key in row.index:
            meta[key] = clean_value(row.get(key))

    if not meta.get("province_norm") and meta.get("province"):
        meta["province_norm"] = make_norm_key(meta.get("province"))

    if not meta.get("city_norm") and meta.get("city"):
        meta["city_norm"] = make_norm_key(meta.get("city"))

    if not meta.get("area_norm") and meta.get("area"):
        meta["area_norm"] = make_norm_key(meta.get("area"))

    return meta


def build_place_text(row: pd.Series) -> str:
    return text_join([
        f"Tên địa điểm: {row.get('name')}",
        f"Tên khác: {json_to_text(row.get('aliases_json'))}",
        f"Tỉnh/thành: {row.get('province')}",
        f"Khu vực: {row.get('area')}",
        f"Nhóm điểm đến: {row.get('destination_group')}",
        f"Địa chỉ: {row.get('address')}",
        f"Loại hình chính: {row.get('category_main')}",
        f"Loại hình phụ: {row.get('category_sub')}",
        f"Tags: {json_to_text(row.get('tags_json'))}",
        f"Sở thích phù hợp: {json_to_text(row.get('interest_tags_json'))}",
        f"Mô tả ngắn: {row.get('short_description')}",
        f"Mô tả: {row.get('description')}",
        f"Điểm chất lượng: {row.get('quality_score')}",
    ])


def build_constraint_text(row: pd.Series) -> str:
    return text_join([
        f"Địa điểm: {row.get('name')}",
        f"Tỉnh/thành: {row.get('province')}",
        f"Ngân sách: {row.get('budget_level')} ({row.get('budget_level_norm')})",
        f"Miễn phí: {row.get('is_free')}",
        f"Phí vào cửa dự kiến: {row.get('entry_fee_min')} - {row.get('entry_fee_max')}",
        f"Mức đi bộ: {row.get('walking_level')} ({row.get('walking_level_norm')})",
        f"Mức vận động: {row.get('activity_level')} ({row.get('activity_level_norm')})",
        f"Phù hợp trẻ em: {row.get('kid_friendly_norm')}",
        f"Phù hợp người lớn tuổi: {row.get('elderly_friendly_norm')}",
        f"Phù hợp cho: {json_to_text(row.get('suitable_for_json'))}",
        f"Nên tránh cho: {json_to_text(row.get('avoid_for_json'))}",
        f"Ghi chú giá: {row.get('price_note')}",
    ])


def build_itinerary_text(row: pd.Series) -> str:
    return text_join([
        f"Địa điểm: {row.get('name')}",
        f"Tỉnh/thành: {row.get('province')}",
        f"Khu vực: {row.get('area')}",
        f"Loại hình: {row.get('category_main')} - {row.get('category_sub')}",
        f"Buổi phù hợp: {row.get('suggested_slot')} ({row.get('slot_norm')})",
        f"Thời điểm tốt trong ngày: {json_to_text(row.get('best_time_of_day_json'))}",
        f"Thời lượng gợi ý: {row.get('duration_minutes')} phút",
        f"Giờ mở cửa: {row.get('open_time')}",
        f"Giờ đóng cửa: {row.get('close_time')}",
        f"Vai trò lịch trình: {row.get('recommended_use')} ({row.get('recommended_use_norm')})",
        f"Không nên xếp làm điểm chính: {row.get('must_not_schedule_as_main')}",
        f"Khoảng cách từ trung tâm: {row.get('distance_from_center_km')} km",
        f"Khu vực gần đó: {json_to_text(row.get('nearby_area_json'))}",
        f"Gợi ý di chuyển: {json_to_text(row.get('transport_suggestion_json'))}",
    ])


def build_realtime_text(row: pd.Series) -> str:
    return text_join([
        f"Địa điểm: {row.get('name')}",
        f"Tỉnh/thành: {row.get('province')}",
        f"Cần kiểm tra realtime: {row.get('requires_realtime_check')}",
        f"Các trường cần kiểm tra realtime: {json_to_text(row.get('realtime_fields_json'))}",
        f"Giờ mở cửa hiện có: {row.get('open_time')}",
        f"Giờ đóng cửa hiện có: {row.get('close_time')}",
        f"Giá vé hiện có: {row.get('entry_fee_min')} - {row.get('entry_fee_max')}",
        f"Nguồn: {row.get('source')}",
        f"URL nguồn: {row.get('source_url')}",
        f"Cập nhật lần cuối: {row.get('last_updated')}",
    ])


def make_doc(row: pd.Series, doc_type: str, text: str) -> dict[str, Any]:
    place_id = str(row.get("place_id")).strip()
    metadata = base_metadata(row)
    metadata["doc_type"] = doc_type

    return {
        "doc_id": f"{doc_type}::{place_id}",
        "doc_type": doc_type,
        "place_id": place_id,
        "title": strip_text(row.get("name")) or place_id,
        "text": text,
        "metadata": metadata,
    }


def main() -> None:
    df, input_file = load_places_dataframe()

    docs = []
    doc_type_counts = {
        "place": 0,
        "constraint": 0,
        "itinerary": 0,
        "realtime": 0,
    }

    for _, row in df.iterrows():
        place_text = build_place_text(row)
        constraint_text = build_constraint_text(row)
        itinerary_text = build_itinerary_text(row)
        realtime_text = build_realtime_text(row)

        for doc_type, text in [
            ("place", place_text),
            ("constraint", constraint_text),
            ("itinerary", itinerary_text),
            ("realtime", realtime_text),
        ]:
            doc = make_doc(row, doc_type, text)
            docs.append(doc)
            doc_type_counts[doc_type] += 1

    settings.rag_documents_file.parent.mkdir(parents=True, exist_ok=True)

    with settings.rag_documents_file.open("w", encoding="utf-8") as f:
        for doc in docs:
            f.write(json.dumps(doc, ensure_ascii=False) + "\n")

    report = {
        "input_file": str(input_file),
        "output_file": str(settings.rag_documents_file),
        "place_count": int(len(df)),
        "document_count": int(len(docs)),
        "doc_type_counts": doc_type_counts,
        "sample_documents": docs[:4],
    }

    report_path = settings.reports_dir / "build_rag_documents_report.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Input file: {input_file}")
    print(f"Saved RAG documents: {settings.rag_documents_file}")
    print(f"Saved report: {report_path}")
    print(f"Places: {len(df)}")
    print(f"Documents: {len(docs)}")
    print(f"Doc type counts: {doc_type_counts}")


if __name__ == "__main__":
    main()