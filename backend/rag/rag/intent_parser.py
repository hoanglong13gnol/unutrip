import re
from dataclasses import dataclass, field

from rag.text_utils import normalize_text


PROVINCE_ALIASES = {
    "ha noi": "ha_noi",
    "hanoi": "ha_noi",

    "da nang": "da_nang",
    "danang": "da_nang",

    "phu tho": "phu_tho",
    "phutho": "phu_tho",

    "an giang": "an_giang",
    "angiang": "an_giang",

    "khanh hoa": "khanh_hoa",
    "nha trang": "khanh_hoa",
    "nhatrang": "khanh_hoa",

    "tp ho chi minh": "tp_ho_chi_minh",
    "ho chi minh": "tp_ho_chi_minh",
    "sai gon": "tp_ho_chi_minh",
    "saigon": "tp_ho_chi_minh",

    "hue": "thua_thien_hue",
    "thua thien hue": "thua thien hue",

    "quang ninh": "quang_ninh",
    "ha long": "quang_ninh",

    "hai phong": "hai_phong",
    "can tho": "can_tho",
    "da lat": "lam_dong",
    "lam dong": "lam_dong",
    "sapa": "lao_cai",
    "sa pa": "lao_cai",
    "lao cai": "lao_cai",
}


INTEREST_KEYWORDS = {
    "beach": [
        "bien", "bai tam", "dao", "vinh", "bo bien", "tam bien", "ngam bien"
    ],
    "mountain": [
        "nui", "leo nui", "doi", "de deo", "san may"
    ],
    "waterfall": [
        "thac", "suoi"
    ],
    "spiritual": [
        "tam linh", "chua", "den tho", "dinh lang", "mieu",
        "lang mo", "nha tho", "thanh duong"
    ],
    "culture": [
        "van hoa", "lich su", "bao tang", "di tich", "pho co", "kien truc"
    ],
    "food": [
        "an uong", "am thuc", "mon ngon", "nha hang", "quan an", "cafe", "ca phe"
    ],
    "shopping": [
        "mua sam", "cho noi", "cho dem", "cho dia phuong",
        "trung tam thuong mai", "qua luu niem"
    ],
    "checkin": [
        "check in", "checkin", "chup anh", "song ao", "view dep", "canh dep"
    ],
    "nature": [
        "thien nhien", "sinh thai", "rung", "ho nuoc", "song nuoc", "mien vuon"
    ],
}


@dataclass
class ParsedIntent:
    raw_query: str
    normalized_query: str

    intent: str = "search_place"

    province_norm: str | None = None
    days: int | None = None
    time_slot: str | None = None

    budget_level: str | None = None
    has_children: bool = False
    has_elderly: bool = False

    walking_preference: str | None = None
    interests: list[str] = field(default_factory=list)
    avoid: list[str] = field(default_factory=list)

    preferred_doc_types: list[str] = field(default_factory=list)


class IntentParser:
    def parse(self, query: str) -> ParsedIntent:
        q = normalize_text(query)

        intent = ParsedIntent(
            raw_query=query,
            normalized_query=q,
        )

        self._detect_intent(q, intent)
        self._detect_province(q, intent)
        self._detect_days(q, intent)
        self._detect_time_slot(q, intent)
        self._detect_budget(q, intent)
        self._detect_people_constraints(q, intent)
        self._detect_walking(q, intent)
        self._detect_interests(q, intent)
        self._set_doc_types(intent)

        return intent

    def _detect_intent(self, q: str, intent: ParsedIntent) -> None:
        if any(x in q for x in ["lich trinh", "ke hoach", "1 ngay", "2 ngay", "3 ngay", "tour"]):
            intent.intent = "itinerary"
        elif any(x in q for x in ["so sanh", "khac nhau", "nen chon"]):
            intent.intent = "compare"
        else:
            intent.intent = "search_place"

    def _detect_province(self, q: str, intent: ParsedIntent) -> None:
        for alias in sorted(PROVINCE_ALIASES.keys(), key=len, reverse=True):
            if self._contains_phrase(q, alias):
                intent.province_norm = PROVINCE_ALIASES[alias]
                return

    def _detect_days(self, q: str, intent: ParsedIntent) -> None:
        match = re.search(r"(\d+)\s*ngay", q)
        if match:
            try:
                intent.days = int(match.group(1))
            except Exception:
                pass

        if "mot ngay" in q or "1 ngay" in q:
            intent.days = 1

    def _detect_time_slot(self, q: str, intent: ParsedIntent) -> None:
        if any(x in q for x in ["buoi sang", "sang som", "sang"]):
            intent.time_slot = "morning"
        if any(x in q for x in ["buoi chieu", "chieu"]):
            intent.time_slot = "afternoon"
        if any(x in q for x in ["buoi toi", "toi", "dem", "ban dem"]):
            intent.time_slot = "evening"

    def _detect_budget(self, q: str, intent: ParsedIntent) -> None:
        if any(x in q for x in ["mien phi", "free", "khong mat phi"]):
            intent.budget_level = "free"
        elif any(x in q for x in ["ngan sach thap", "gia re", "tiet kiem", "it tien"]):
            intent.budget_level = "low"
        elif any(x in q for x in ["trung binh", "vua phai"]):
            intent.budget_level = "medium"
        elif any(x in q for x in ["cao cap", "sang trong", "luxury"]):
            intent.budget_level = "luxury"

    def _detect_people_constraints(self, q: str, intent: ParsedIntent) -> None:
        if any(x in q for x in ["tre em", "tre nho", "em be", "gia dinh", "con nho"]):
            intent.has_children = True

        if any(x in q for x in ["nguoi lon tuoi", "nguoi gia", "ong ba", "bo me", "cao tuoi"]):
            intent.has_elderly = True

    def _detect_walking(self, q: str, intent: ParsedIntent) -> None:
        if any(x in q for x in ["it di bo", "khong di bo nhieu", "di bo it", "nhe nhang", "khong leo"]):
            intent.walking_preference = "easy"
            if "hard_walking" not in intent.avoid:
                intent.avoid.append("hard_walking")

        if any(x in q for x in ["leo nui", "trekking", "van dong nhieu"]):
            intent.walking_preference = "hard"

    def _contains_phrase(self, q: str, phrase: str) -> bool:
        phrase = normalize_text(phrase)

        if not phrase:
            return False

        # Phrase nhiá»u tá»« thÃ¬ match substring.
        if " " in phrase:
            return phrase in q

        # Tá»« Ä‘Æ¡n pháº£i match nguyÃªn token Ä‘á»ƒ trÃ¡nh match nháº§m.
        return re.search(rf"\b{re.escape(phrase)}\b", q) is not None

    def _detect_interests(self, q: str, intent: ParsedIntent) -> None:
        for interest, keywords in INTEREST_KEYWORDS.items():
            matched = False

            for keyword in keywords:
                if self._contains_phrase(q, keyword):
                    matched = True
                    break

            if matched and interest not in intent.interests:
                intent.interests.append(interest)

    def _set_doc_types(self, intent: ParsedIntent) -> None:
        if intent.intent == "itinerary":
            intent.preferred_doc_types = ["itinerary", "constraint", "place"]
        elif intent.has_children or intent.has_elderly or intent.budget_level or intent.walking_preference:
            intent.preferred_doc_types = ["constraint", "place", "itinerary"]
        elif intent.time_slot:
            intent.preferred_doc_types = ["itinerary", "constraint", "place"]
        else:
            intent.preferred_doc_types = ["place", "constraint", "itinerary"]
