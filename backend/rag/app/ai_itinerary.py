from __future__ import annotations

import json
import unicodedata
from datetime import datetime
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from core.config import settings


router = APIRouter(prefix="/ai", tags=["AI Itinerary"])


class ItineraryPreviewRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    startDate: str
    endDate: str
    budget: float | None = None
    preferences: list[str] = Field(default_factory=list)
    province: str | None = None


def normalize_text(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.replace("đ", "d")
    return text


def parse_json_list(value: Any) -> list[Any]:
    if value is None:
        return []

    if isinstance(value, list):
        return value

    if isinstance(value, str):
        value = value.strip()

        if not value:
            return []

        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return parsed
        except Exception:
            return []

    return []


def load_places() -> list[dict[str, Any]]:
    reviewed_file = settings.processed_data_dir / "places_app_reviewed.json"

    if reviewed_file.exists():
        path = reviewed_file
    else:
        path = settings.places_app_file

    if not path.exists():
        return []

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        if isinstance(data.get("data"), list):
            return data["data"]

        if isinstance(data.get("places"), list):
            return data["places"]

    return []


def get_raw_place_id(place: dict[str, Any]) -> str | None:
    raw_id = (
        place.get("place_id")
        or place.get("placeId")
        or place.get("rawPlaceId")
        or place.get("raw_place_id")
        or place.get("id")
    )

    if raw_id is None:
        return None

    return str(raw_id).strip()


def get_numeric_destination_id(place: dict[str, Any]) -> int | None:
    """
    Only returns numeric destinations.id if the source already has it.

    Current RAG data mainly has place_id like AG_0047, so this often returns None.
    Backend Node will later map rawPlaceId -> destinations.id using rag_places.destination_id.
    """

    raw_id = (
        place.get("destination_id")
        or place.get("destinationId")
        or place.get("destination_db_id")
    )

    if raw_id is None:
        return None

    try:
        return int(raw_id)
    except Exception:
        return None


def get_first_image(place: dict[str, Any]) -> str | None:
    images = (
        place.get("images")
        or place.get("images_json")
        or place.get("image_urls")
        or []
    )

    parsed = parse_json_list(images)

    if parsed:
        first = parsed[0]

        if isinstance(first, str):
            return first

        if isinstance(first, dict):
            return (
                first.get("image_url")
                or first.get("imageUrl")
                or first.get("url")
                or first.get("src")
            )

    image_url = place.get("image_url") or place.get("imageUrl")

    if isinstance(image_url, str) and image_url.strip():
        return image_url.strip()

    return None


def get_tags_text(place: dict[str, Any]) -> str:
    tags = (
        place.get("tags")
        or place.get("tags_json")
        or place.get("interest_tags_json")
        or place.get("keywords")
        or []
    )

    parsed = parse_json_list(tags)

    if parsed:
        return " ".join(str(item) for item in parsed)

    if isinstance(tags, str):
        return tags

    return ""


def estimate_trip_days(start_date: str, end_date: str) -> int:
    try:
        start = datetime.fromisoformat(start_date[:10])
        end = datetime.fromisoformat(end_date[:10])
        days = (end - start).days + 1
        return max(1, days)
    except Exception:
        return 1


def app_category_from_rag(place: dict[str, Any]) -> str:
    """
    Map RAG taxonomy to app category for preview display only.

    Important:
    - Do not use full search_text too aggressively, because it contains broad words
      such as "văn hóa", "checkin", "Hồ Tây" that can pollute category mapping.
    - Prefer rawPlaceId/name/category_main/category_sub/tags.
    """

    raw_place_id = normalize_text(get_raw_place_id(place))
    name = normalize_text(place.get("name"))
    main = normalize_text(place.get("category_main_norm") or place.get("category_main"))
    sub = normalize_text(place.get("category_sub_norm") or place.get("category_sub"))
    tags = normalize_text(get_tags_text(place))

    id_name_text = f"{raw_place_id} {name}"
    taxonomy_text = f"{main} {sub} {tags}"
    text = f"{id_name_text} {taxonomy_text}"

    slug_id_name = (
        id_name_text.replace("-", "_")
        .replace("/", "_")
        .replace(" ", "_")
    )

    slug_taxonomy = (
        taxonomy_text.replace("-", "_")
        .replace("/", "_")
        .replace(" ", "_")
    )

    slug_text = f"{slug_id_name} {slug_taxonomy}"

    def norm_key(value: str) -> str:
        return normalize_text(value).replace("-", "_").replace(" ", "_")

    def has_in_id_name(*keywords: str) -> bool:
        for keyword in keywords:
            key = norm_key(keyword)
            if key in slug_id_name:
                return True
        return False

    def has_in_taxonomy(*keywords: str) -> bool:
        for keyword in keywords:
            key = norm_key(keyword)
            if key in slug_taxonomy:
                return True
        return False

    def has_any(*keywords: str) -> bool:
        for keyword in keywords:
            key = norm_key(keyword)
            if key in slug_text:
                return True
        return False

    # 1. Exact / strong place-name rules.
    if has_in_id_name(
        "ho hoan kiem",
        "ho-hoan-kiem",
        "ho_hoan_kiem",
        "ho tay",
        "ho-tay",
        "ho_tay",
        "cau the huc",
        "cau-the-huc",
        "cau_the_huc",
        "pho di bo ho guom",
        "pho-di-bo-ho-guom",
        "pho_di_bo_ho_guom"
    ):
        return "checkin"

    if has_in_id_name(
        "pho co ha noi",
        "pho-co-ha-noi",
        "pho_co_ha_noi"
    ):
        return "city"

    if has_in_id_name(
        "van mieu",
        "van-mieu",
        "van_mieu",
        "quoc tu giam",
        "quoc-tu-giam",
        "quoc_tu_giam",
        "hoang thanh",
        "hoang-thanh",
        "hoang_thanh",
        "hoa lo",
        "hoa-lo",
        "hoa_lo",
        "nha tu",
        "nha-tu",
        "nha_tu",
        "lang co",
        "lang-co",
        "lang_co",
        "duong lam",
        "duong-lam",
        "duong_lam",
        "bao tang",
        "bao-tang",
        "bao_tang"
    ):
        return "heritage"

    if has_in_id_name(
        "chua",
        "den",
        "phu",
        "nha tho",
        "nha-tho",
        "nha_tho",
        "tran quoc",
        "tran-quoc",
        "tran_quoc",
        "quan thanh",
        "quan-thanh",
        "quan_thanh",
        "phu tay ho",
        "phu-tay-ho",
        "phu_tay_ho",
        "kim lien",
        "kim-lien",
        "kim_lien",
        "ngoc son",
        "ngoc-son",
        "ngoc_son"
    ):
        return "religious"

    if has_in_id_name(
        "bat trang",
        "bat-trang",
        "bat_trang",
        "lang gom",
        "lang-gom",
        "lang_gom",
        "lang lua",
        "lang-lua",
        "lang_lua",
        "van phuc",
        "van-phuc",
        "van_phuc",
        "lang huong",
        "lang-huong",
        "lang_huong",
        "quang phu cau",
        "quang-phu-cau",
        "quang_phu_cau",
        "mua roi",
        "mua-roi",
        "mua_roi",
        "nha hat",
        "nha-hat",
        "nha_hat",
        "lang van hoa",
        "lang-van-hoa",
        "lang_van_hoa"
    ):
        return "culture"

    if has_in_id_name(
        "vuon quoc gia ba vi",
        "vuon-quoc-gia-ba-vi",
        "vuon_quoc_gia_ba_vi",
        "ba vi",
        "ba-vi",
        "ba_vi"
    ):
        return "mountain"

    # 2. Food.
    if has_any(
        "am thuc",
        "am-thuc",
        "am_thuc",
        "food",
        "dac san",
        "dac-san",
        "dac_san",
        "an uong",
        "an-uong",
        "an_uong",
        "pho bia",
        "pho-bia",
        "pho_bia",
        "pho ca phe",
        "pho-ca-phe",
        "pho_ca_phe",
        "cho dem",
        "cho-dem",
        "cho_dem",
        "cho dong xuan",
        "cho-dong-xuan",
        "cho_dong_xuan",
        "lang ran",
        "lang-ran",
        "lang_ran"
    ):
        return "food"

    # 3. Religious from taxonomy.
    if has_in_taxonomy(
        "tam linh",
        "tam-linh",
        "tam_linh",
        "ton giao",
        "ton-giao",
        "ton_giao",
        "chua",
        "den",
        "phu",
        "thien vien",
        "thien-vien",
        "thien_vien",
        "nha tho",
        "nha-tho",
        "nha_tho",
        "pagoda",
        "temple"
    ):
        return "religious"

    # 4. Heritage/history/museum.
    if has_in_taxonomy(
        "di tich",
        "di-tich",
        "di_tich",
        "lich su",
        "lich-su",
        "lich_su",
        "bao tang",
        "bao-tang",
        "bao_tang",
        "heritage",
        "museum",
        "di san",
        "di-san",
        "di_san"
    ):
        return "heritage"

    # 5. Culture/community/craft villages.
    if has_in_taxonomy(
        "van hoa cong dong",
        "van-hoa-cong-dong",
        "van_hoa_cong_dong",
        "lang nghe",
        "lang-nghe",
        "lang_nghe",
        "le hoi",
        "le-hoi",
        "le_hoi",
        "dan toc",
        "dan-toc",
        "dan_toc",
        "mua roi",
        "mua-roi",
        "mua_roi"
    ):
        return "culture"

    # 6. Real beach / sea / island only.
    is_urban_lake = has_in_id_name(
        "ho hoan kiem",
        "ho-hoan-kiem",
        "ho_hoan_kiem",
        "ho tay",
        "ho-tay",
        "ho_tay"
    )

    if not is_urban_lake and has_in_taxonomy(
        "bai bien",
        "bai-bien",
        "bai_bien",
        "bai tam",
        "bai-tam",
        "bai_tam",
        "bien",
        "dao",
        "vinh",
        "hon",
        "mui",
        "cu lao",
        "cu-lao",
        "cu_lao",
        "cang bien",
        "cang-bien",
        "cang_bien"
    ):
        return "beach"

    # 7. Mountain/nature adventure.
    if has_in_taxonomy(
        "nui",
        "thac",
        "hang",
        "cao nguyen",
        "cao-nguyen",
        "cao_nguyen",
        "doi cat",
        "doi-cat",
        "doi_cat",
        "suoi",
        "vuon quoc gia",
        "vuon-quoc-gia",
        "vuon_quoc_gia"
    ):
        return "mountain"

    # 8. City/urban.
    if has_any(
        "thanh pho",
        "thanh-pho",
        "thanh_pho",
        "do thi",
        "do-thi",
        "do_thi",
        "pho co",
        "pho-co",
        "pho_co",
        "old quarter",
        "old-quarter",
        "old_quarter",
        "street",
        "khu pho",
        "khu-pho",
        "khu_pho"
    ):
        return "city"

    return "nature"


def score_place(place: dict[str, Any], request: ItineraryPreviewRequest) -> int:
    score = 0

    app_category = app_category_from_rag(place)

    province = normalize_text(place.get("province"))
    city = normalize_text(place.get("city"))
    area = normalize_text(place.get("area"))

    searchable = " ".join(
        [
            normalize_text(place.get("name")),
            normalize_text(place.get("description")),
            normalize_text(place.get("short_description")),
            normalize_text(place.get("category_main")),
            normalize_text(place.get("category_sub")),
            normalize_text(place.get("category_main_norm")),
            normalize_text(place.get("category_sub_norm")),
            normalize_text(place.get("province")),
            normalize_text(place.get("city")),
            normalize_text(place.get("area")),
            normalize_text(get_tags_text(place)),
            normalize_text(place.get("search_text")),
            app_category,
        ]
    )

    if request.province:
        requested_province = normalize_text(request.province)

        if requested_province and (
            requested_province in province
            or requested_province in city
            or requested_province in area
            or province in requested_province
            or city in requested_province
        ):
            score += 100

    for pref in request.preferences:
        pref_norm = normalize_text(pref)

        if not pref_norm:
            continue

        if pref_norm == app_category:
            score += 60
        elif pref_norm in searchable:
            score += 30

    description = normalize_text(request.description)

    for word in description.split():
        if len(word) >= 3 and word in searchable:
            score += 4

    quality = (
        place.get("quality_score")
        or place.get("rating")
        or place.get("score")
        or 0
    )

    try:
        score += int(float(quality))
    except Exception:
        pass

    return score


def build_reason(place: dict[str, Any], request: ItineraryPreviewRequest) -> str:
    category = app_category_from_rag(place)
    province = place.get("province") or place.get("city") or ""
    prefs = ", ".join(request.preferences) if request.preferences else "nhu cầu du lịch"

    if province:
        return f"Phù hợp với {prefs}, thuộc nhóm {category}, nằm tại {province}."

    return f"Phù hợp với {prefs}, thuộc nhóm {category}."


@router.post("/itinerary-preview")
def itinerary_preview(request: ItineraryPreviewRequest) -> dict[str, Any]:
    places = load_places()

    if not places:
        return {
            "success": False,
            "message": "Không tìm thấy dữ liệu địa điểm cho RAG preview.",
            "data": {
                "title": request.title or "Lịch trình AI gợi ý",
                "summary": "Không có dữ liệu địa điểm.",
                "suggestedDestinations": [],
            },
        }

    scored: list[tuple[int, dict[str, Any]]] = []

    for place in places:
        raw_place_id = get_raw_place_id(place)

        if not raw_place_id:
            continue

        score = score_place(place, request)

        if score > 0:
            scored.append((score, place))

    # If filters are too strict, fallback to valid active places.
    if not scored:
        scored = [
            (0, place)
            for place in places
            if get_raw_place_id(place)
        ]

    scored.sort(key=lambda item: item[0], reverse=True)

    trip_days = estimate_trip_days(request.startDate, request.endDate)
    suggestions: list[dict[str, Any]] = []

    used_raw_place_ids: set[str] = set()

    for index, (_, place) in enumerate(scored):
        if len(suggestions) >= 20:
            break

        raw_place_id = get_raw_place_id(place)

        if not raw_place_id or raw_place_id in used_raw_place_ids:
            continue

        used_raw_place_ids.add(raw_place_id)

        destination_id = get_numeric_destination_id(place)

        suggestions.append(
            {
                # May be null at preview stage.
                # Node backend will map rawPlaceId -> destinations.id before saving.
                "destinationId": destination_id,
                "rawPlaceId": raw_place_id,
                "name": place.get("name"),
                "province": place.get("province"),
                "city": place.get("city"),
                "area": place.get("area"),
                "category": app_category_from_rag(place),
                "imageUrl": get_first_image(place),
                "reason": build_reason(place, request),
                "estimatedVisitDurationMinutes": int(place.get("duration_minutes") or 120),
                "recommendedDay": (index % trip_days) + 1,
                "qualityScore": place.get("quality_score"),
            }
        )

    return {
        "success": True,
        "data": {
            "title": request.title or "Lịch trình AI gợi ý",
            "summary": "AI/RAG đã gợi ý danh sách địa điểm. Bạn có thể chọn/bỏ chọn trước khi tạo lịch trình.",
            "suggestedDestinations": suggestions,
        },
    }
# ==================== AI ITINERARY OPTIONS ====================

class AIItineraryOptionDay(BaseModel):
    dayNumber: int
    items: list[dict[str, Any]] = Field(default_factory=list)


class AIItineraryOption(BaseModel):
    optionId: str
    title: str
    summary: str
    theme: str
    estimatedBudget: float | None = None
    totalDays: int
    highlights: list[str] = Field(default_factory=list)
    days: list[AIItineraryOptionDay] = Field(default_factory=list)


def build_suggestion_item(
    place: dict[str, Any],
    recommended_day: int,
) -> dict[str, Any]:
    return {
        "destinationId": get_numeric_destination_id(place),
        "rawPlaceId": get_raw_place_id(place),
        "name": place.get("name"),
        "province": place.get("province"),
        "city": place.get("city"),
        "area": place.get("area"),
        "category": app_category_from_rag(place),
        "imageUrl": get_first_image(place),
        "reason": build_reason(
            place,
            ItineraryPreviewRequest(
                title="",
                description="",
                startDate="2026-01-01",
                endDate="2026-01-01",
                budget=None,
                preferences=[],
                province=place.get("province"),
            ),
        ),
        "estimatedVisitDurationMinutes": int(place.get("duration_minutes") or 120),
        "recommendedDay": recommended_day,
        "qualityScore": place.get("quality_score"),
    }


def rank_places_for_option(
    places: list[dict[str, Any]],
    request: ItineraryPreviewRequest,
    option_preferences: list[str],
    option_keywords: list[str],
    limit: int,
) -> list[dict[str, Any]]:
    option_request = ItineraryPreviewRequest(
        title=request.title,
        description=" ".join(
            [
                request.description or "",
                " ".join(option_keywords),
            ]
        ).strip(),
        startDate=request.startDate,
        endDate=request.endDate,
        budget=request.budget,
        preferences=option_preferences,
        province=request.province,
    )

    scored: list[tuple[int, dict[str, Any]]] = []

    for place in places:
        raw_place_id = get_raw_place_id(place)

        if not raw_place_id:
            continue

        if str(place.get("is_active", True)).lower() in {"false", "0", "no"}:
            continue

        score = score_place(place, option_request)

        category = app_category_from_rag(place)
        if category in option_preferences:
            score += 35

        searchable = normalize_text(
            " ".join(
                [
                    str(place.get("name") or ""),
                    str(place.get("description") or ""),
                    str(place.get("short_description") or ""),
                    str(place.get("search_text") or ""),
                    get_tags_text(place),
                ]
            )
        )

        for keyword in option_keywords:
            if normalize_text(keyword) in searchable:
                score += 12

        try:
            score += int(float(place.get("quality_score") or 0))
        except Exception:
            pass

        if score > 0:
            scored.append((score, place))

    if not scored:
        scored = [
            (0, place)
            for place in places
            if get_raw_place_id(place)
        ]

    scored.sort(key=lambda item: item[0], reverse=True)

    selected: list[dict[str, Any]] = []
    used_ids: set[str] = set()

    for _, place in scored:
        raw_place_id = get_raw_place_id(place)

        if not raw_place_id or raw_place_id in used_ids:
            continue

        used_ids.add(raw_place_id)
        selected.append(place)

        if len(selected) >= limit:
            break

    return selected


def distribute_places_to_days(
    places: list[dict[str, Any]],
    total_days: int,
    max_items_per_day: int = 3,
) -> list[AIItineraryOptionDay]:
    days = [
        AIItineraryOptionDay(dayNumber=day_number, items=[])
        for day_number in range(1, total_days + 1)
    ]

    max_total_items = total_days * max_items_per_day
    selected_places = places[:max_total_items]

    for index, place in enumerate(selected_places):
        day_index = index % total_days
        recommended_day = day_index + 1
        days[day_index].items.append(
            build_suggestion_item(place, recommended_day)
        )

    return days


def build_option_summary(theme: str, province: str | None) -> str:
    location = province or "khu vực bạn chọn"

    if theme == "balanced":
        return f"Lịch trình cân bằng cho {location}, kết hợp check-in, văn hóa và trải nghiệm địa phương."

    if theme == "checkin":
        return f"Tập trung các điểm nổi bật, dễ chụp ảnh và phù hợp cho chuyến đi check-in tại {location}."

    if theme == "food_culture":
        return f"Ưu tiên ẩm thực, văn hóa, làng nghề và trải nghiệm đời sống địa phương tại {location}."

    if theme == "relax_nature":
        return f"Lịch trình nhẹ nhàng hơn, ưu tiên thiên nhiên, cảnh quan và ít áp lực di chuyển tại {location}."

    return f"Phương án tour gợi ý cho {location}."


def build_itinerary_option(
    request: ItineraryPreviewRequest,
    places: list[dict[str, Any]],
    option_id: str,
    title: str,
    theme: str,
    option_preferences: list[str],
    option_keywords: list[str],
    max_items_per_day: int,
) -> AIItineraryOption:
    total_days = estimate_trip_days(request.startDate, request.endDate)
    ranked_places = rank_places_for_option(
        places=places,
        request=request,
        option_preferences=option_preferences,
        option_keywords=option_keywords,
        limit=max(12, total_days * max_items_per_day + 4),
    )

    days = distribute_places_to_days(
        places=ranked_places,
        total_days=total_days,
        max_items_per_day=max_items_per_day,
    )

    highlights: list[str] = []
    for day in days:
        for item in day.items:
            name = item.get("name")
            if name and name not in highlights:
                highlights.append(str(name))
            if len(highlights) >= 5:
                break
        if len(highlights) >= 5:
            break

    return AIItineraryOption(
        optionId=option_id,
        title=title,
        summary=build_option_summary(theme, request.province),
        theme=theme,
        estimatedBudget=request.budget,
        totalDays=total_days,
        highlights=highlights,
        days=days,
    )


@router.post("/itinerary-options")
def itinerary_options(request: ItineraryPreviewRequest) -> dict[str, Any]:
    places = load_places()

    if not places:
        return {
            "success": False,
            "message": "Không tìm thấy dữ liệu địa điểm cho RAG itinerary options.",
            "data": {
                "title": request.title or "Lịch trình AI gợi ý",
                "summary": "Không có dữ liệu địa điểm.",
                "options": [],
            },
        }

    province_label = request.province or "điểm đến"

    option_specs = [
        {
            "option_id": "balanced",
            "title": f"{province_label} cân bằng",
            "theme": "balanced",
            "preferences": list(dict.fromkeys(request.preferences + ["checkin", "culture", "food"])),
            "keywords": ["checkin", "van hoa", "am thuc", "trai nghiem"],
            "max_items_per_day": 3,
        },
        {
            "option_id": "checkin",
            "title": f"{province_label} check-in nổi bật",
            "theme": "checkin",
            "preferences": list(dict.fromkeys(["checkin", "city", "nature"] + request.preferences)),
            "keywords": ["checkin", "canh dep", "noi bat", "song ao", "quang truong"],
            "max_items_per_day": 3,
        },
        {
            "option_id": "food_culture",
            "title": f"{province_label} ẩm thực và văn hóa",
            "theme": "food_culture",
            "preferences": list(dict.fromkeys(["food", "culture", "heritage"] + request.preferences)),
            "keywords": ["am thuc", "dac san", "van hoa", "lang nghe", "cho", "pho"],
            "max_items_per_day": 3,
        },
        {
            "option_id": "relax_nature",
            "title": f"{province_label} nhẹ nhàng thiên nhiên",
            "theme": "relax_nature",
            "preferences": list(dict.fromkeys(["nature", "mountain", "checkin"] + request.preferences)),
            "keywords": ["thien nhien", "ho", "nui", "vuon", "suoi", "thu gian"],
            "max_items_per_day": 2,
        },
    ]

    options = [
        build_itinerary_option(
            request=request,
            places=places,
            option_id=spec["option_id"],
            title=spec["title"],
            theme=spec["theme"],
            option_preferences=spec["preferences"],
            option_keywords=spec["keywords"],
            max_items_per_day=spec["max_items_per_day"],
        )
        for spec in option_specs
    ]

    return {
        "success": True,
        "data": {
            "title": request.title or "Lịch trình AI gợi ý",
            "summary": "AI/RAG đã tạo nhiều phương án tour. Bạn có thể chọn một tour rồi chỉnh sửa địa điểm trước khi lưu.",
            "options": [option.model_dump() for option in options],
        },
    }