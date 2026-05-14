from dataclasses import asdict
from typing import Any

from core.config import settings
from rag.bm25_retriever import BM25Retriever
from rag.fusion import reciprocal_rank_fusion
from rag.intent_parser import IntentParser, ParsedIntent
from rag.text_utils import normalize_text


class HybridRetriever:
    def __init__(self) -> None:
        self._last_fusion_debug: dict[str, Any] = {}
        self.intent_parser = IntentParser()
        self.bm25 = BM25Retriever()
        self.bm25.load()

    def retrieve(self, query: str, top_k: int = 8) -> dict[str, Any]:
        intent = self.intent_parser.parse(query)

        raw_results = self._lexical_candidates(
            query=query,
            intent=intent,
        )

        scored = []
        for item in raw_results:
            rerank_score, reasons = self._travel_rule_score(item, intent)
            final_score = float(item["score"]) + rerank_score

            enriched = dict(item)
            enriched["bm25_score"] = item["score"]
            enriched["rule_score"] = round(rerank_score, 4)
            enriched["final_score"] = round(final_score, 4)
            enriched["reasons"] = reasons

            scored.append(enriched)

        scored.sort(key=lambda x: x["final_score"], reverse=True)

        deduped = []
        seen_place_ids = set()
        seen_name_keys = set()

        for item in scored:
            place_id = item.get("place_id")
            if not place_id or place_id in seen_place_ids:
                continue

            name_key = self._name_dedup_key(item.get("title"))

            if name_key and name_key in seen_name_keys:
                continue

            seen_place_ids.add(place_id)

            if name_key:
                seen_name_keys.add(name_key)

            deduped.append(item)

            if len(deduped) >= top_k:
                break

        return {
            "query": query,
            "intent": asdict(intent),
            "results": deduped,
            "debug": {
                "raw_count": len(raw_results),
                "scored_count": len(scored),
                "final_count": len(deduped),
                "fusion": self._last_fusion_debug,
            },
        }

    def _lexical_candidates(self, query: str, intent: ParsedIntent) -> list[dict[str, Any]]:
        self._last_fusion_debug: dict[str, Any] = {"mode": "bm25_only"}

        bm25_hits = self.bm25.search(
            query=query,
            top_k=120,
            doc_types=intent.preferred_doc_types,
            province_norm=intent.province_norm,
        )

        use_rrf = (
            settings.enable_rrf_fusion
            and self.bm25.has_tfidf()
        )

        if not use_rrf:
            return bm25_hits

        tfidf_hits = self.bm25.search_tfidf(
            query=query,
            top_k=120,
            doc_types=intent.preferred_doc_types,
            province_norm=intent.province_norm,
        )

        if not tfidf_hits:
            self._last_fusion_debug = {"mode": "bm25_only", "reason": "tfidf_empty"}
            return bm25_hits

        bm25_ids = [str(h["doc_id"]) for h in bm25_hits if h.get("doc_id")]
        tfidf_ids = [str(h["doc_id"]) for h in tfidf_hits if h.get("doc_id")]
        rrf_scores = reciprocal_rank_fusion([bm25_ids, tfidf_ids], k=60.0)

        by_id: dict[str, dict[str, Any]] = {}
        for h in bm25_hits:
            did = h.get("doc_id")
            if did:
                by_id[str(did)] = dict(h)

        for h in tfidf_hits:
            did = h.get("doc_id")
            if did and str(did) not in by_id:
                by_id[str(did)] = dict(h)

        fused_order = sorted(rrf_scores.keys(), key=lambda d: rrf_scores[d], reverse=True)

        fused: list[dict[str, Any]] = []
        for doc_id in fused_order:
            item = by_id.get(doc_id)
            if not item:
                continue
            enriched = dict(item)
            enriched["score"] = round(rrf_scores[doc_id] * 400.0 + float(enriched.get("score", 0.0)) * 0.01, 4)
            enriched["rrf_score"] = round(rrf_scores[doc_id], 6)
            fused.append(enriched)
            if len(fused) >= 120:
                break

        self._last_fusion_debug = {
            "mode": "rrf_bm25_tfidf",
            "bm25_count": len(bm25_hits),
            "tfidf_count": len(tfidf_hits),
            "fused_count": len(fused),
        }
        return fused
    def _name_dedup_key(self, title: str | None) -> str:
        name = normalize_text(str(title or ""))

        remove_phrases = [
            "khu du lich",
            "diem du lich",
            "dia diem",
            "bai bien",
            "bai tam",
            "khu bao ton",
            "quan the di tich",
            "di tich",
            "chua",
            "den",
            "dinh",
            "nha tho",
        ]

        for phrase in remove_phrases:
            name = name.replace(phrase, " ")

        tokens = [
            token
            for token in name.split()
            if token not in {
                "tai",
                "o",
                "tp",
                "thanh",
                "pho",
                "nha",
                "trang",
                "ha",
                "noi",
                "hue",
            }
        ]

        # Nếu bỏ hết token thì fallback về normalized name gốc.
        if not tokens:
            return normalize_text(str(title or ""))

        return " ".join(tokens)

    def _is_near_duplicate_name(self, a: str | None, b: str | None) -> bool:
        key_a = self._name_dedup_key(a)
        key_b = self._name_dedup_key(b)

        if not key_a or not key_b:
            return False

        if key_a == key_b:
            return True

        tokens_a = set(key_a.split())
        tokens_b = set(key_b.split())

        if not tokens_a or not tokens_b:
            return False

        overlap = len(tokens_a & tokens_b)
        smaller = min(len(tokens_a), len(tokens_b))

        return overlap / smaller >= 0.8

    def _travel_rule_score(self, item: dict[str, Any], intent: ParsedIntent) -> tuple[float, list[str]]:
        meta = item.get("metadata") or {}
        score = 0.0
        reasons: list[str] = []

        if intent.province_norm and meta.get("province_norm") == intent.province_norm:
            score += 15
            reasons.append("match_province")

        doc_type = item.get("doc_type")
        if intent.intent == "itinerary":
            if doc_type == "itinerary":
                score += 8
                reasons.append("itinerary_doc")
            elif doc_type == "constraint":
                score += 4
                reasons.append("constraint_doc")
        else:
            if doc_type == "place":
                score += 4
                reasons.append("place_doc")
            elif doc_type == "constraint":
                score += 3
                reasons.append("constraint_doc")

        budget = meta.get("budget_level_norm")
        if intent.budget_level:
            if intent.budget_level == "free":
                if budget == "free":
                    score += 12
                    reasons.append("match_free_budget")
                else:
                    score -= 10
                    reasons.append("not_free")
            elif intent.budget_level == "low":
                if budget in {"free", "low", "low_medium"}:
                    score += 10
                    reasons.append("match_low_budget")
                elif budget in {"high", "luxury"}:
                    score -= 8
                    reasons.append("budget_too_high")

        if intent.has_children:
            if meta.get("kid_friendly_norm") is True:
                score += 10
                reasons.append("kid_friendly")
            elif meta.get("kid_friendly_norm") is False:
                score -= 15
                reasons.append("not_kid_friendly")

        if intent.has_elderly:
            if meta.get("elderly_friendly_norm") is True:
                score += 12
                reasons.append("elderly_friendly")
            elif meta.get("elderly_friendly_norm") is False:
                score -= 18
                reasons.append("not_elderly_friendly")

            walking = meta.get("walking_level_norm")
            if walking == "easy":
                score += 8
                reasons.append("easy_walking")
            elif walking == "moderate":
                score += 2
                reasons.append("moderate_walking")
            elif walking == "hard":
                score -= 15
                reasons.append("hard_walking_penalty")

        if intent.walking_preference == "easy":
            walking = meta.get("walking_level_norm")
            if walking == "easy":
                score += 8
                reasons.append("match_easy_walking")
            elif walking == "hard":
                score -= 15
                reasons.append("avoid_hard_walking")

        if intent.time_slot:
            slot = meta.get("slot_norm")
            if intent.time_slot == slot:
                score += 10
                reasons.append("match_time_slot")
            elif slot in {"any", "full_day"}:
                score += 4
                reasons.append("flexible_slot")
            else:
                score -= 4
                reasons.append("slot_mismatch")

        if intent.interests:
            interest_score, interest_reasons = self._interest_score(
                item=item,
                meta=meta,
                interests=intent.interests,
            )
            score += interest_score
            reasons.extend(interest_reasons)

        quality = meta.get("quality_score")
        try:
            if quality is not None:
                q = float(quality)
                score += min(max(q, 0), 10) * 1.5
                reasons.append("quality_score")
        except Exception:
            pass

        recommended = meta.get("recommended_use_norm")
        if recommended == "main":
            score += 6
            reasons.append("recommended_main")
        elif recommended == "supporting":
            score += 3
            reasons.append("recommended_supporting")
        elif recommended == "optional":
            score -= 3
            reasons.append("optional_penalty")

        if intent.intent == "itinerary" and meta.get("must_not_schedule_as_main") is True:
            score -= 20
            reasons.append("must_not_schedule_as_main_penalty")

        if meta.get("requires_realtime_check") is True:
            score -= 1
            reasons.append("requires_realtime_check")

        return score, reasons

    def _interest_score(
        self,
        item: dict[str, Any],
        meta: dict[str, Any],
        interests: list[str],
    ) -> tuple[float, list[str]]:
        score = 0.0
        reasons: list[str] = []

        title = str(item.get("title") or "")
        doc_text = str(item.get("text") or "")

        category = str(meta.get("category_main_norm") or "")
        sub = str(meta.get("category_sub_norm") or "")
        raw_category = str(meta.get("category_main") or "")
        raw_sub = str(meta.get("category_sub") or "")

        title_norm = normalize_text(title)

        text = " ".join([
            title,
            category,
            sub,
            raw_category,
            raw_sub,
            doc_text[:600],
        ])
        text_norm = normalize_text(text)

        for interest in interests:
            if interest == "beach":
                beach_score, beach_reasons = self._beach_score(
                    title_norm=title_norm,
                    text_norm=text_norm,
                )
                score += beach_score
                reasons.extend(beach_reasons)

            elif interest == "spiritual":
                if any(x in text_norm for x in [
                    "tam linh", "chua", "den", "dinh", "mieu", "nha tho", "temple", "spiritual"
                ]):
                    score += 12
                    reasons.append("match_spiritual")

            elif interest == "culture":
                if any(x in text_norm for x in [
                    "van hoa", "lich su", "bao tang", "di tich", "pho co", "culture", "history", "museum"
                ]):
                    score += 10
                    reasons.append("match_culture")

            elif interest == "food":
                if any(x in text_norm for x in [
                    "am thuc", "nha hang", "quan an", "cafe", "ca phe", "food"
                ]):
                    score += 10
                    reasons.append("match_food")

            elif interest == "checkin":
                if any(x in text_norm for x in [
                    "checkin", "check in", "chup anh", "song ao", "view", "canh dep"
                ]):
                    score += 8
                    reasons.append("match_checkin")

            elif interest == "nature":
                if any(x in text_norm for x in [
                    "thien nhien", "sinh thai", "rung", "ho", "song", "park", "eco", "nature"
                ]):
                    score += 8
                    reasons.append("match_nature")

        return score, reasons

    def _beach_score(self, title_norm: str, text_norm: str) -> tuple[float, list[str]]:
        score = 0.0
        reasons: list[str] = []

        exact_good_titles = [
            "doc let",
            "bai bien doc let",
            "bai tien nha trang",
            "dao khi nha trang",
            "bien nha trang",
            "khu bao ton bien hon mun",
        ]

        title_strong_beach_terms = [
            "bai bien",
            "bien",
            "dao",
            "vinh",
            "hon",
            "doc let",
            "bai tien",
            "hon mun",
        ]

        context_beach_terms = [
            "bien dao",
            "bai tam",
            "hai san",
            "nghi duong",
            "cano",
            "tau",
            "beach",
            "island",
            "bay",
            "coast",
        ]

        title_non_beach_terms = [
            "suoi",
            "thac",
            "dinh",
            "nui",
            "rung",
            "ho",
            "deo",
            "hang",
            "nha tho nui",
            "dinh bao dai",
            "vien hai duong hoc",
            "cap treo",
            "khu pho tay",
        ]

        if any(term in title_norm for term in exact_good_titles):
            score += 24
            reasons.append("exact_beach_title_match")
        elif any(term in title_norm for term in title_strong_beach_terms):
            score += 18
            reasons.append("strong_beach_title_match")
        elif any(term in text_norm for term in context_beach_terms):
            score += 6
            reasons.append("weak_beach_context_match")
        else:
            score -= 10
            reasons.append("missing_beach_signal")

        if any(term in title_norm for term in title_non_beach_terms):
            score -= 35
            reasons.append("non_beach_title_penalty")

        return score, reasons