import time
from typing import Any

from core.config import settings
from rag.hybrid_retriever import HybridRetriever
from rag.context_builder import ContextBuilder
from rag.prompt_builder import PromptBuilder
from rag.logger import AiRequestLogger
from llm.response_cache import ResponseCache
from rag.place_store import PlaceStore


class RagPipeline:
    def __init__(self) -> None:
        self.retriever = HybridRetriever()
        self.context_builder = ContextBuilder()
        self.prompt_builder = PromptBuilder()
        self.ai_logger = AiRequestLogger()
        self.response_cache = ResponseCache()
        self.place_store = PlaceStore()

        self.gemini_generator = None

        if settings.enable_gemini and settings.ai_runtime_mode in {
            "demo",
            "gemini_only",
            "hybrid",
        }:
            try:
                from llm.gemini_generator import GeminiGenerator

                self.gemini_generator = GeminiGenerator()
            except Exception as exc:
                print(f"[WARN] Gemini generator init failed: {exc}")
                self.gemini_generator = None

    import time
from typing import Any

from core.config import settings
from rag.hybrid_retriever import HybridRetriever
from rag.context_builder import ContextBuilder
from rag.prompt_builder import PromptBuilder
from rag.logger import AiRequestLogger
from llm.response_cache import ResponseCache
from rag.place_store import PlaceStore


class RagPipeline:
    def __init__(self) -> None:
        self.retriever = HybridRetriever()
        self.context_builder = ContextBuilder()
        self.prompt_builder = PromptBuilder()
        self.ai_logger = AiRequestLogger()
        self.response_cache = ResponseCache()
        self.place_store = PlaceStore()

        self.gemini_generator = None

        if settings.enable_gemini and settings.ai_runtime_mode in {
            "demo",
            "gemini_only",
            "hybrid",
        }:
            try:
                from llm.gemini_generator import GeminiGenerator

                self.gemini_generator = GeminiGenerator()
            except Exception as exc:
                print(f"[WARN] Gemini generator init failed: {exc}")
                self.gemini_generator = None

    def _normalize_filter_text(self, value) -> str:
            if not value:
                return ""

            import unicodedata

            text = str(value).strip().lower()
            text = unicodedata.normalize("NFD", text)
            text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
            text = text.replace("đ", "d")
            text = " ".join(text.split())
            return text

    def _place_matches_province(self, place: dict[str, Any], target_province) -> bool:
        target = self._normalize_filter_text(target_province)
        if not target:
            return True

        meta = place.get("metadata") or {}

        province = self._normalize_filter_text(
            place.get("province") or meta.get("province")
        )
        city = self._normalize_filter_text(
            place.get("city") or meta.get("city")
        )
        area = self._normalize_filter_text(
            place.get("area") or meta.get("area")
        )

        return (
            province == target
            or target in province
            or province in target
            or city == target
            or area == target
        )

    def _filter_retrieved_by_province(
        self,
        retrieved: dict[str, Any],
        target_province,
        top_k: int,
    ) -> dict[str, Any]:
        if not target_province:
            return retrieved

        results = retrieved.get("results", []) or []

        filtered = [
            item for item in results
            if self._place_matches_province(item, target_province)
        ]

        if filtered:
            new_retrieved = dict(retrieved)
            new_retrieved["results"] = filtered[:top_k]

            debug = dict(new_retrieved.get("debug") or {})
            debug["province_filter"] = target_province
            debug["province_filter_used"] = True
            debug["province_filter_source"] = "retrieved"
            debug["province_filter_count"] = len(filtered)
            new_retrieved["debug"] = debug

            return new_retrieved

        return retrieved

    def _province_fallback_retrieved(
        self,
        query: str,
        retrieved: dict[str, Any],
        target_province,
        top_k: int,
    ) -> dict[str, Any]:
        if not target_province:
            return retrieved

        try:
            places = self.place_store.search(
                q=None,
                province=target_province,
                active_only=True,
                limit=top_k,
            )
        except TypeError:
            places = self.place_store.search(
                province=target_province,
                limit=top_k,
            )

        if not places:
            return retrieved

        fallback_results = []

        for place in places:
            metadata = dict(place)

            place_id = (
                place.get("place_id")
                or place.get("raw_place_id")
                or place.get("id")
            )

            name = (
                place.get("name")
                or place.get("title")
                or "Địa điểm"
            )

            item = {
                "place_id": place_id,
                "title": name,
                "metadata": metadata,
                "score": place.get("search_score", 1.0),
                "final_score": place.get("search_score", 1.0),
                "reasons": ["province_fallback"],
            }

            fallback_results.append(item)

        new_retrieved = dict(retrieved)
        new_retrieved["results"] = fallback_results[:top_k]

        debug = dict(new_retrieved.get("debug") or {})
        debug["province_filter"] = target_province
        debug["province_filter_used"] = True
        debug["province_filter_source"] = "place_store_fallback"
        debug["province_fallback_count"] = len(fallback_results)
        new_retrieved["debug"] = debug

        return new_retrieved

    def run(
        self,
        query: str,
        top_k: int = 6,
        mode: str = "balanced",
        include_prompt: bool = True,
        target_province=None,
        target_city=None,
    ) -> dict[str, Any]:
        started = time.perf_counter()

        t0 = time.perf_counter()
        retrieved = self.retriever.retrieve(query, top_k=top_k)

        if target_province:
            retrieved = self._filter_retrieved_by_province(
                retrieved=retrieved,
                target_province=target_province,
                top_k=top_k,
            )

            filtered_results = retrieved.get("results", []) or []
            has_target_result = any(
                self._place_matches_province(item, target_province)
                for item in filtered_results
            )

            if not has_target_result:
                retrieved = self._province_fallback_retrieved(
                    query=query,
                    retrieved=retrieved,
                    target_province=target_province,
                    top_k=top_k,
                )

        retrieval_ms = (time.perf_counter() - t0) * 1000

        t1 = time.perf_counter()
        context = self.context_builder.build_context(retrieved, max_places=top_k)
        context_ms = (time.perf_counter() - t1) * 1000

        t2 = time.perf_counter()
        prompt = self.prompt_builder.build_prompt(retrieved, context)
        prompt_ms = (time.perf_counter() - t2) * 1000

        place_ids_for_cache = [
            item.get("place_id")
            for item in retrieved.get("results", [])[:top_k]
            if item.get("place_id")
        ]

        cache_key = self.response_cache.make_key(
            query=query,
            runtime_mode=settings.ai_runtime_mode,
            model_name=settings.gemini_model,
            place_ids=place_ids_for_cache,
        )

        generation_started = time.perf_counter()
        answer_payload = self._generate_answer(
            prompt=prompt,
            retrieved=retrieved,
            query=query,
            cache_key=cache_key,
        )
        generation_ms = (time.perf_counter() - generation_started) * 1000

        total_ms = (time.perf_counter() - started) * 1000

        response = {
            "answer": answer_payload["answer"],
            "rag_mode": mode,
            "runtime_mode": settings.ai_runtime_mode,
            "model_used": answer_payload["model_used"],
            "fallback_used": answer_payload.get("fallback_used", False),
            "places": self._extract_places(retrieved),
            "warnings": self._extract_warnings(retrieved),
            "latency_ms": {
                "retrieval": round(retrieval_ms, 2),
                "context": round(context_ms, 2),
                "prompt": round(prompt_ms, 2),
                "generation": round(generation_ms, 2),
                "gemini": answer_payload.get("gemini_latency_ms", 0),
                "total": round(total_ms, 2),
            },
            "debug": {
                "intent": retrieved.get("intent"),
                "retriever_debug": retrieved.get("debug"),
                "target_province": target_province,
                "target_city": target_city,
                "prompt_chars": len(prompt),
                "context_chars": len(context),
                "generation_error": answer_payload.get("error"),
                "generation_error_type": answer_payload.get("error_type"),
                "retry_after_seconds": answer_payload.get("retry_after_seconds"),
                "gemini_timeout": answer_payload.get("gemini_timeout", False),
                "cache_hit": answer_payload.get("cache_hit", False),
            },
        }

        if include_prompt:
            response["prompt"] = prompt
            response["context"] = context

        self._log_request(query=query, response=response)

        return response
        try:
            places = response.get("places", [])
            debug = response.get("debug", {})

            record = {
                "query": query,
                "runtime_mode": response.get("runtime_mode"),
                "rag_mode": response.get("rag_mode"),
                "model_used": response.get("model_used"),
                "fallback_used": response.get("fallback_used"),
                "latency_ms": response.get("latency_ms", {}),
                "top_place_ids": [
                    place.get("place_id") for place in places[:10]
                ],
                "top_place_names": [
                    place.get("name") for place in places[:10]
                ],
                "warnings_count": len(response.get("warnings", [])),
                "generation_error": debug.get("generation_error"),
                "generation_error_type": debug.get("generation_error_type"),
                "retry_after_seconds": debug.get("retry_after_seconds"),
                "gemini_timeout": debug.get("gemini_timeout", False),
                "cache_hit": debug.get("cache_hit", False),
                "intent": debug.get("intent"),
            }

            self.ai_logger.log(record)
        except Exception as exc:
            print(f"[WARN] Failed to write AI request log: {exc}")

    def _generate_answer(
        self,
        prompt: str,
        retrieved: dict[str, Any],
        query: str,
        cache_key: str,
    ) -> dict[str, Any]:
        runtime_mode = settings.ai_runtime_mode

        if runtime_mode in {"demo", "gemini_only"}:
            return self._generate_with_gemini_or_template(
                prompt=prompt,
                retrieved=retrieved,
                query=query,
                cache_key=cache_key,
            )

        if runtime_mode == "retrieval_only":
            return {
                "answer": self._build_template_answer(retrieved),
                "model_used": "retrieval_template",
                "fallback_used": True,
                "gemini_latency_ms": 0,
                "gemini_timeout": False,
                "error": None,
                "error_type": None,
                "retry_after_seconds": None,
                "cache_hit": False,
            }

        if runtime_mode == "mock":
            return {
                "answer": self._build_mock_answer(retrieved),
                "model_used": "mock",
                "fallback_used": False,
                "gemini_latency_ms": 0,
                "gemini_timeout": False,
                "error": None,
                "error_type": None,
                "retry_after_seconds": None,
                "cache_hit": False,
            }

        if runtime_mode == "hybrid":
            # Tạm thời chưa gắn LoRA, nên hybrid sẽ dùng Gemini.
            # Sau này đổi thành: LoRA -> Validator -> Gemini fallback.
            return self._generate_with_gemini_or_template(
                prompt=prompt,
                retrieved=retrieved,
                query=query,
                cache_key=cache_key,
            )

        return {
            "answer": self._build_template_answer(retrieved),
            "model_used": "unknown_runtime_template",
            "fallback_used": True,
            "gemini_latency_ms": 0,
            "gemini_timeout": False,
            "error": f"Unknown AI_RUNTIME_MODE={runtime_mode}",
            "error_type": "config_error",
            "retry_after_seconds": None,
            "cache_hit": False,
        }

    def _generate_with_gemini_or_template(
        self,
        prompt: str,
        retrieved: dict[str, Any],
        query: str,
        cache_key: str,
    ) -> dict[str, Any]:
        cached = self.response_cache.get(cache_key)
        if cached:
            return {
                "answer": cached.get("answer", ""),
                "model_used": cached.get("model_used", "gemini_cache"),
                "fallback_used": False,
                "gemini_latency_ms": 0,
                "gemini_timeout": False,
                "error": None,
                "error_type": None,
                "retry_after_seconds": None,
                "cache_hit": True,
            }

        if self.gemini_generator is None:
            return {
                "answer": self._build_template_answer(retrieved),
                "model_used": "template_no_gemini",
                "fallback_used": True,
                "gemini_latency_ms": 0,
                "gemini_timeout": False,
                "error": "Gemini generator is not available",
                "error_type": "gemini_not_available",
                "retry_after_seconds": None,
                "cache_hit": False,
            }

        result = self.gemini_generator.generate(prompt)

        if result.get("ok") and result.get("answer"):
            answer_text = result["answer"]

            self.response_cache.set(
                cache_key,
                {
                    "query": query,
                    "answer": answer_text,
                    "model_used": result["model_used"],
                    "runtime_mode": settings.ai_runtime_mode,
                },
            )

            return {
                "answer": answer_text,
                "model_used": result["model_used"],
                "fallback_used": False,
                "gemini_latency_ms": result.get("latency_ms", 0),
                "gemini_timeout": False,
                "error": None,
                "error_type": None,
                "retry_after_seconds": None,
                "cache_hit": False,
            }

        error_text = result.get("error")
        error_type = result.get("error_type")
        retry_after_seconds = result.get("retry_after_seconds")

        is_timeout = bool(result.get("timeout", False))

        if error_text and "timeout" in str(error_text).lower():
            is_timeout = True

        return {
            "answer": self._build_template_answer(retrieved),
            "model_used": "template_after_gemini_error",
            "fallback_used": True,
            "gemini_latency_ms": result.get("latency_ms", 0),
            "gemini_timeout": is_timeout,
            "error": error_text,
            "error_type": error_type,
            "retry_after_seconds": retry_after_seconds,
            "cache_hit": False,
        }

    def _extract_places(self, retrieved: dict[str, Any]) -> list[dict[str, Any]]:
        places = []

        for item in retrieved.get("results", []):
            meta = item.get("metadata") or {}

            places.append({
                "place_id": item.get("place_id"),
                "name": item.get("title"),
                "province": meta.get("province"),
                "city": meta.get("city"),
                "area": meta.get("area"),
                "category_main": meta.get("category_main"),
                "category_sub": meta.get("category_sub"),
                "budget_level": meta.get("budget_level_norm"),
                "walking_level": meta.get("walking_level_norm"),
                "kid_friendly": meta.get("kid_friendly_norm"),
                "elderly_friendly": meta.get("elderly_friendly_norm"),
                "slot": meta.get("slot_norm"),
                "quality_score": meta.get("quality_score"),
                "recommended_use": meta.get("recommended_use_norm"),
                "requires_realtime_check": meta.get("requires_realtime_check"),
                "score": item.get("final_score"),
                "reasons": item.get("reasons", []),
            })

        return places

    def _extract_warnings(self, retrieved: dict[str, Any]) -> list[str]:
        warnings = []
        seen = set()

        for item in retrieved.get("results", []):
            meta = item.get("metadata") or {}
            name = item.get("title")

            if meta.get("requires_realtime_check") is True and name not in seen:
                warnings.append(
                    f"Nên kiểm tra thông tin thực tế trước khi đi {name}, đặc biệt là giờ mở cửa, giá vé hoặc điều kiện vận hành."
                )
                seen.add(name)

        return warnings

    def _build_mock_answer(self, retrieved: dict[str, Any]) -> str:
        intent = retrieved.get("intent", {})
        results = retrieved.get("results", [])

        if not results:
            return "Mình chưa tìm thấy địa điểm phù hợp trong dữ liệu hiện có."

        names = [item.get("title") for item in results[:5]]

        if intent.get("intent") == "itinerary":
            return (
                "Đây là câu trả lời mock. Pipeline đã truy xuất được các địa điểm phù hợp để lập lịch trình: "
                + ", ".join(names)
                + "."
            )

        return (
            "Đây là câu trả lời mock. Pipeline đã truy xuất được các địa điểm phù hợp: "
            + ", ".join(names)
            + "."
        )

    def _build_template_answer(self, retrieved: dict[str, Any]) -> str:
        results = retrieved.get("results", [])

        if not results:
            return "Mình chưa tìm thấy địa điểm phù hợp trong dữ liệu hiện có."

        lines = [
            "Mình đã tìm được một số địa điểm phù hợp từ dữ liệu UnuTrip:",
            "",
        ]

        for index, item in enumerate(results[:5], start=1):
            meta = item.get("metadata") or {}
            name = item.get("title")
            province = meta.get("province")
            walking = meta.get("walking_level_norm")
            budget = meta.get("budget_level_norm")

            lines.append(
                f"{index}. {name} ({province}) - ngân sách: {budget}, mức đi bộ: {walking}."
            )

        lines.append("")
        lines.append(
            "Dựa trên kết quả truy xuất, các địa điểm trên phù hợp với nhu cầu của bạn. Nếu muốn đi nhẹ nhàng và tiết kiệm, nên ưu tiên các điểm có ngân sách free và mức đi bộ easy. Nếu muốn trải nghiệm phong phú hơn, bạn có thể kết hợp thêm các điểm đảo/vịnh hoặc hoạt động tham quan gần khu vực."
        )

        return "\n".join(lines)
    def run(
        self,
        query: str,
        top_k: int = 6,
        mode: str = "balanced",
        include_prompt: bool = True,
        target_province: str | None = None,
        target_city: str | None = None,
    ) -> dict[str, Any]:
        started = time.perf_counter()

        t0 = time.perf_counter()
        retrieved = self.retriever.retrieve(query, top_k=top_k)

        if target_province:
            retrieved = self._filter_retrieved_by_province(
                retrieved=retrieved,
                target_province=target_province,
                top_k=top_k,
            )

            filtered_results = retrieved.get("results", []) or []
            has_target_result = any(
                self._place_matches_province(item, target_province)
                for item in filtered_results
            )

            if not has_target_result:
                retrieved = self._province_fallback_retrieved(
                    query=query,
                    retrieved=retrieved,
                    target_province=target_province,
                    top_k=top_k,
                )

                retrieval_ms = (time.perf_counter() - t0) * 1000

        t1 = time.perf_counter()
        context = self.context_builder.build_context(retrieved, max_places=top_k)
        context_ms = (time.perf_counter() - t1) * 1000

        t2 = time.perf_counter()
        prompt = self.prompt_builder.build_prompt(retrieved, context)
        prompt_ms = (time.perf_counter() - t2) * 1000

        place_ids_for_cache = [
            item.get("place_id")
            for item in retrieved.get("results", [])[:top_k]
            if item.get("place_id")
        ]

        cache_key = self.response_cache.make_key(
            query=query,
            runtime_mode=settings.ai_runtime_mode,
            model_name=settings.gemini_model,
            place_ids=place_ids_for_cache,
        )

        generation_started = time.perf_counter()
        answer_payload = self._generate_answer(
            prompt=prompt,
            retrieved=retrieved,
            query=query,
            cache_key=cache_key,
        )
        generation_ms = (time.perf_counter() - generation_started) * 1000

        total_ms = (time.perf_counter() - started) * 1000

        response = {
            "answer": answer_payload["answer"],
            "rag_mode": mode,
            "runtime_mode": settings.ai_runtime_mode,
            "model_used": answer_payload["model_used"],
            "fallback_used": answer_payload.get("fallback_used", False),
            "places": self._extract_places(retrieved),
            "warnings": self._extract_warnings(retrieved),
            "latency_ms": {
                "retrieval": round(retrieval_ms, 2),
                "context": round(context_ms, 2),
                "prompt": round(prompt_ms, 2),
                "generation": round(generation_ms, 2),
                "gemini": answer_payload.get("gemini_latency_ms", 0),
                "total": round(total_ms, 2),
            },
            "debug": {
                "intent": retrieved.get("intent"),
                "retriever_debug": retrieved.get("debug"),
                "prompt_chars": len(prompt),
                "context_chars": len(context),
                "generation_error": answer_payload.get("error"),
                "generation_error_type": answer_payload.get("error_type"),
                "retry_after_seconds": answer_payload.get("retry_after_seconds"),
                "gemini_timeout": answer_payload.get("gemini_timeout", False),
                "cache_hit": answer_payload.get("cache_hit", False),
            },
        }

        if include_prompt:
            response["prompt"] = prompt
            response["context"] = context

        self._log_request(query=query, response=response)

        return response
    
    
    
    def _log_request(self, query: str, response: dict[str, Any]) -> None:
        try:
            places = response.get("places", [])
            debug = response.get("debug", {})

            record = {
                "query": query,
                "runtime_mode": response.get("runtime_mode"),
                "rag_mode": response.get("rag_mode"),
                "model_used": response.get("model_used"),
                "fallback_used": response.get("fallback_used"),
                "latency_ms": response.get("latency_ms", {}),
                "top_place_ids": [
                    place.get("place_id") for place in places[:10]
                ],
                "top_place_names": [
                    place.get("name") for place in places[:10]
                ],
                "warnings_count": len(response.get("warnings", [])),
                "generation_error": debug.get("generation_error"),
                "generation_error_type": debug.get("generation_error_type"),
                "retry_after_seconds": debug.get("retry_after_seconds"),
                "gemini_timeout": debug.get("gemini_timeout", False),
                "cache_hit": debug.get("cache_hit", False),
                "intent": debug.get("intent"),
            }

            self.ai_logger.log(record)
        except Exception as exc:
            print(f"[WARN] Failed to write AI request log: {exc}")

    def _generate_answer(
        self,
        prompt: str,
        retrieved: dict[str, Any],
        query: str,
        cache_key: str,
    ) -> dict[str, Any]:
        runtime_mode = settings.ai_runtime_mode

        if runtime_mode in {"demo", "gemini_only"}:
            return self._generate_with_gemini_or_template(
                prompt=prompt,
                retrieved=retrieved,
                query=query,
                cache_key=cache_key,
            )

        if runtime_mode == "retrieval_only":
            return {
                "answer": self._build_template_answer(retrieved),
                "model_used": "retrieval_template",
                "fallback_used": True,
                "gemini_latency_ms": 0,
                "gemini_timeout": False,
                "error": None,
                "error_type": None,
                "retry_after_seconds": None,
                "cache_hit": False,
            }

        if runtime_mode == "mock":
            return {
                "answer": self._build_mock_answer(retrieved),
                "model_used": "mock",
                "fallback_used": False,
                "gemini_latency_ms": 0,
                "gemini_timeout": False,
                "error": None,
                "error_type": None,
                "retry_after_seconds": None,
                "cache_hit": False,
            }

        if runtime_mode == "hybrid":
            # Tạm thời chưa gắn LoRA, nên hybrid sẽ dùng Gemini.
            # Sau này đổi thành: LoRA -> Validator -> Gemini fallback.
            return self._generate_with_gemini_or_template(
                prompt=prompt,
                retrieved=retrieved,
                query=query,
                cache_key=cache_key,
            )

        return {
            "answer": self._build_template_answer(retrieved),
            "model_used": "unknown_runtime_template",
            "fallback_used": True,
            "gemini_latency_ms": 0,
            "gemini_timeout": False,
            "error": f"Unknown AI_RUNTIME_MODE={runtime_mode}",
            "error_type": "config_error",
            "retry_after_seconds": None,
            "cache_hit": False,
        }

    def _generate_with_gemini_or_template(
        self,
        prompt: str,
        retrieved: dict[str, Any],
        query: str,
        cache_key: str,
    ) -> dict[str, Any]:
        cached = self.response_cache.get(cache_key)
        if cached:
            return {
                "answer": cached.get("answer", ""),
                "model_used": cached.get("model_used", "gemini_cache"),
                "fallback_used": False,
                "gemini_latency_ms": 0,
                "gemini_timeout": False,
                "error": None,
                "error_type": None,
                "retry_after_seconds": None,
                "cache_hit": True,
            }

        if self.gemini_generator is None:
            return {
                "answer": self._build_template_answer(retrieved),
                "model_used": "template_no_gemini",
                "fallback_used": True,
                "gemini_latency_ms": 0,
                "gemini_timeout": False,
                "error": "Gemini generator is not available",
                "error_type": "gemini_not_available",
                "retry_after_seconds": None,
                "cache_hit": False,
            }

        result = self.gemini_generator.generate(prompt)

        if result.get("ok") and result.get("answer"):
            answer_text = result["answer"]

            self.response_cache.set(
                cache_key,
                {
                    "query": query,
                    "answer": answer_text,
                    "model_used": result["model_used"],
                    "runtime_mode": settings.ai_runtime_mode,
                },
            )

            return {
                "answer": answer_text,
                "model_used": result["model_used"],
                "fallback_used": False,
                "gemini_latency_ms": result.get("latency_ms", 0),
                "gemini_timeout": False,
                "error": None,
                "error_type": None,
                "retry_after_seconds": None,
                "cache_hit": False,
            }

        error_text = result.get("error")
        error_type = result.get("error_type")
        retry_after_seconds = result.get("retry_after_seconds")

        is_timeout = bool(result.get("timeout", False))

        if error_text and "timeout" in str(error_text).lower():
            is_timeout = True

        return {
            "answer": self._build_template_answer(retrieved),
            "model_used": "template_after_gemini_error",
            "fallback_used": True,
            "gemini_latency_ms": result.get("latency_ms", 0),
            "gemini_timeout": is_timeout,
            "error": error_text,
            "error_type": error_type,
            "retry_after_seconds": retry_after_seconds,
            "cache_hit": False,
        }

    def _extract_places(self, retrieved: dict[str, Any]) -> list[dict[str, Any]]:
        places = []

        for item in retrieved.get("results", []):
            meta = item.get("metadata") or {}

            places.append({
                "place_id": item.get("place_id"),
                "name": item.get("title"),
                "province": meta.get("province"),
                "city": meta.get("city"),
                "area": meta.get("area"),
                "category_main": meta.get("category_main"),
                "category_sub": meta.get("category_sub"),
                "budget_level": meta.get("budget_level_norm"),
                "walking_level": meta.get("walking_level_norm"),
                "kid_friendly": meta.get("kid_friendly_norm"),
                "elderly_friendly": meta.get("elderly_friendly_norm"),
                "slot": meta.get("slot_norm"),
                "quality_score": meta.get("quality_score"),
                "recommended_use": meta.get("recommended_use_norm"),
                "requires_realtime_check": meta.get("requires_realtime_check"),
                "score": item.get("final_score"),
                "reasons": item.get("reasons", []),
            })

        return places

    def _extract_warnings(self, retrieved: dict[str, Any]) -> list[str]:
        warnings = []
        seen = set()

        for item in retrieved.get("results", []):
            meta = item.get("metadata") or {}
            name = item.get("title")

            if meta.get("requires_realtime_check") is True and name not in seen:
                warnings.append(
                    f"Nên kiểm tra thông tin thực tế trước khi đi {name}, đặc biệt là giờ mở cửa, giá vé hoặc điều kiện vận hành."
                )
                seen.add(name)

        return warnings

    def _build_mock_answer(self, retrieved: dict[str, Any]) -> str:
        intent = retrieved.get("intent", {})
        results = retrieved.get("results", [])

        if not results:
            return "Mình chưa tìm thấy địa điểm phù hợp trong dữ liệu hiện có."

        names = [item.get("title") for item in results[:5]]

        if intent.get("intent") == "itinerary":
            return (
                "Đây là câu trả lời mock. Pipeline đã truy xuất được các địa điểm phù hợp để lập lịch trình: "
                + ", ".join(names)
                + "."
            )

        return (
            "Đây là câu trả lời mock. Pipeline đã truy xuất được các địa điểm phù hợp: "
            + ", ".join(names)
            + "."
        )

    def _build_template_answer(self, retrieved: dict[str, Any]) -> str:
        results = retrieved.get("results", [])

        if not results:
            return "Mình chưa tìm thấy địa điểm phù hợp trong dữ liệu hiện có."

        lines = [
            "Mình đã tìm được một số địa điểm phù hợp từ dữ liệu UnuTrip:",
            "",
        ]

        for index, item in enumerate(results[:5], start=1):
            meta = item.get("metadata") or {}
            name = item.get("title")
            province = meta.get("province")
            walking = meta.get("walking_level_norm")
            budget = meta.get("budget_level_norm")

            lines.append(
                f"{index}. {name} ({province}) - ngân sách: {budget}, mức đi bộ: {walking}."
            )

        lines.append("")
        lines.append(
            "Dựa trên kết quả truy xuất, các địa điểm trên phù hợp với nhu cầu của bạn. Nếu muốn đi nhẹ nhàng và tiết kiệm, nên ưu tiên các điểm có ngân sách free và mức đi bộ easy. Nếu muốn trải nghiệm phong phú hơn, bạn có thể kết hợp thêm các điểm đảo/vịnh hoặc hoạt động tham quan gần khu vực."
        )

        return "\n".join(lines)