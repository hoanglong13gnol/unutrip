import json
from typing import Any

from core.config import settings
from rag.text_utils import normalize_text


class PlaceStore:
    def __init__(self) -> None:
        self.places_by_id: dict[str, dict[str, Any]] = {}
        self.loaded = False
        self.source_file = self._select_source_file()
        self.load()

    def _select_source_file(self):
        reviewed_file = settings.processed_data_dir / "places_app_reviewed.json"

        if reviewed_file.exists():
            return reviewed_file

        return settings.places_app_file

    def load(self) -> None:
        self.places_by_id = {}
        self.source_file = self._select_source_file()

        if not self.source_file.exists():
            self.loaded = False
            return

        data = json.loads(self.source_file.read_text(encoding="utf-8"))

        if isinstance(data, list):
            places = data
        elif isinstance(data, dict):
            places = data.get("places", [])
        else:
            places = []

        for place in places:
            place_id = place.get("place_id")
            if place_id:
                self.places_by_id[str(place_id)] = place

        self.loaded = True

    def get(self, place_id: str) -> dict[str, Any] | None:
        return self.places_by_id.get(place_id)

    def search(
        self,
        q: str | None = None,
        province: str | None = None,
        category: str | None = None,
        active_only: bool = True,
        limit: int = 20,
        min_score: float | None = None,
    ) -> list[dict[str, Any]]:
        q_norm = normalize_text(q or "").strip()
        province_norm = normalize_text(province or "").strip()
        category_norm = normalize_text(category or "").strip()

        limit = max(1, min(limit, 100))

        scored: list[tuple[float, dict[str, Any]]] = []

        for place in self.places_by_id.values():
            if active_only and place.get("is_active") is False:
                continue

            if province_norm:
                place_province_norm = normalize_text(
                    str(place.get("province_norm") or "")
                )
                place_province_text = normalize_text(
                    str(place.get("province") or "")
                )

                accepted_provinces = {
                    place_province_norm,
                    place_province_text,
                    place_province_text.replace(" ", "_"),
                }

                if province_norm not in accepted_provinces:
                    continue

            if category_norm:
                cat_main = normalize_text(str(place.get("category_main") or ""))
                cat_sub = normalize_text(str(place.get("category_sub") or ""))
                cat_main_norm = normalize_text(
                    str(place.get("category_main_norm") or "")
                )
                cat_sub_norm = normalize_text(
                    str(place.get("category_sub_norm") or "")
                )

                category_blob = " ".join([
                    cat_main,
                    cat_sub,
                    cat_main_norm,
                    cat_sub_norm,
                ])

                if category_norm not in category_blob:
                    continue

            score = self._search_score(place, q_norm)

            if q_norm and score <= 0:
                continue

            if min_score is not None and score < min_score:
                continue

            scored.append((score, place))

        scored.sort(
            key=lambda item: (
                item[0],
                float(item[1].get("quality_score") or 0),
            ),
            reverse=True,
        )

        return [
            self._compact_place(place, score)
            for score, place in scored[:limit]
        ]

    def _search_score(self, place: dict[str, Any], q_norm: str) -> float:
        if not q_norm:
            return 1.0

        name = normalize_text(str(place.get("name") or ""))
        place_id = normalize_text(str(place.get("place_id") or ""))
        aliases = normalize_text(str(place.get("aliases_json") or ""))
        search_text = normalize_text(str(place.get("search_text") or ""))

        score = 0.0

        if q_norm == place_id:
            score += 100

        if q_norm == name:
            score += 80
        elif name.startswith(q_norm):
            score += 60
        elif q_norm in name:
            score += 45

        if q_norm in aliases:
            score += 30

        if q_norm in search_text:
            score += 15

        query_tokens = set(q_norm.split())
        blob_tokens = set(search_text.split())

        if query_tokens:
            overlap = len(query_tokens & blob_tokens)
            score += overlap * 5

        return score

    def _compact_place(self, place: dict[str, Any], score: float) -> dict[str, Any]:
        return {
            "place_id": place.get("place_id"),
            "name": place.get("name"),
            "province": place.get("province"),
            "city": place.get("city"),
            "area": place.get("area"),
            "category_main": place.get("category_main"),
            "category_sub": place.get("category_sub"),
            "budget_level": place.get("budget_level_norm"),
            "walking_level": place.get("walking_level_norm"),
            "kid_friendly": place.get("kid_friendly_norm"),
            "elderly_friendly": place.get("elderly_friendly_norm"),
            "quality_score": place.get("quality_score"),
            "recommended_use": place.get("recommended_use_norm"),
            "requires_realtime_check": place.get("requires_realtime_check"),
            "is_active": place.get("is_active"),
            "search_score": round(score, 4),
        }

    def status(self) -> dict[str, Any]:
        return {
            "loaded": self.loaded,
            "source_file": str(self.source_file),
            "place_count": len(self.places_by_id),
            "using_reviewed": self.source_file.name == "places_app_reviewed.json",
        }