"""Application service: RAG chat + retrieval (wraps RagPipeline)."""

from __future__ import annotations

from typing import Any

from rag.pipeline import RagPipeline


def _as_place_id(value: object) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    return s or None


class RagService:
    def __init__(self, pipeline: RagPipeline) -> None:
        self._pipeline = pipeline

    def rag_chat(
        self,
        message: str,
        top_k: int,
        mode: str,
        include_prompt: bool,
    ) -> dict[str, Any]:
        return self._pipeline.run(
            query=message,
            top_k=top_k,
            mode=mode,
            include_prompt=include_prompt,
        )

    def rag_retrieve(self, message: str, top_k: int) -> dict[str, Any]:
        retrieved = self._pipeline.retriever.retrieve(
            query=message,
            top_k=top_k,
        )
        return {
            "query": message,
            "intent": retrieved.get("intent"),
            "debug": retrieved.get("debug"),
            "results": retrieved.get("results"),
        }

    def rag_chat_simple(
        self,
        message: str,
        top_k: int,
        mode: str,
        target_province: str | None,
        target_city: str | None,
    ) -> dict[str, Any]:
        result = self._pipeline.run(
            query=message,
            top_k=top_k,
            mode=mode,
            include_prompt=False,
            target_province=target_province,
            target_city=target_city,
        )

        simple_places = []
        for place in result.get("places", []):
            pid = _as_place_id(place.get("place_id")) or _as_place_id(place.get("raw_place_id"))
            simple_places.append({
                "place_id": pid,
                "name": place.get("name"),
                "province": place.get("province"),
                "city": place.get("city"),
                "area": place.get("area"),
                "category_main": place.get("category_main"),
                "category_sub": place.get("category_sub"),
                "budget_level": place.get("budget_level"),
                "walking_level": place.get("walking_level"),
                "kid_friendly": place.get("kid_friendly"),
                "elderly_friendly": place.get("elderly_friendly"),
                "slot": place.get("slot"),
                "quality_score": place.get("quality_score"),
                "recommended_use": place.get("recommended_use"),
                "requires_realtime_check": place.get("requires_realtime_check"),
                "score": place.get("score"),
            })

        return {
            "answer": result.get("answer"),
            "places": simple_places,
            "warnings": result.get("warnings", []),
            "latency_ms": result.get("latency_ms", {}),
            "model_used": result.get("model_used", "mock"),
            "fallback_used": result.get("fallback_used", False),
            "rag_mode": result.get("rag_mode", mode),
            "runtime_mode": result.get("runtime_mode"),
        }
