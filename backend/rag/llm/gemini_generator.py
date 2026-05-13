import re
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from typing import Any

from google import genai

from core.config import settings


class GeminiGenerator:
    def __init__(self) -> None:
        if not settings.gemini_api_key:
            raise ValueError(
                "Missing GEMINI_API_KEY. Please set GEMINI_API_KEY in .env"
            )

        self.model_name = settings.gemini_model
        self.timeout_seconds = settings.gemini_timeout_seconds
        self.client = genai.Client(api_key=settings.gemini_api_key)

    def generate(self, prompt: str) -> dict[str, Any]:
        started = time.perf_counter()

        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(self._generate_sync, prompt)

        try:
            text = future.result(timeout=self.timeout_seconds)
            latency_ms = (time.perf_counter() - started) * 1000

            executor.shutdown(wait=False, cancel_futures=True)

            if not text:
                text = "Dữ liệu hiện chưa đủ để tạo câu trả lời chi tiết."

            return {
                "ok": True,
                "answer": text.strip(),
                "model_used": self.model_name,
                "latency_ms": round(latency_ms, 2),
                "timeout": False,
                "error": None,
                "error_type": None,
                "retry_after_seconds": None,
            }

        except FutureTimeoutError:
            latency_ms = (time.perf_counter() - started) * 1000

            future.cancel()
            executor.shutdown(wait=False, cancel_futures=True)

            return {
                "ok": False,
                "answer": "",
                "model_used": self.model_name,
                "latency_ms": round(latency_ms, 2),
                "timeout": True,
                "error": f"Gemini timeout after {self.timeout_seconds}s",
                "error_type": "timeout",
                "retry_after_seconds": None,
            }

        except Exception as exc:
            latency_ms = (time.perf_counter() - started) * 1000

            executor.shutdown(wait=False, cancel_futures=True)

            error_text = str(exc)
            error_type = self._classify_error(error_text)
            retry_after_seconds = self._extract_retry_after_seconds(error_text)

            return {
                "ok": False,
                "answer": "",
                "model_used": self.model_name,
                "latency_ms": round(latency_ms, 2),
                "timeout": False,
                "error": self._short_error_message(error_type, error_text),
                "error_type": error_type,
                "retry_after_seconds": retry_after_seconds,
                "raw_error": error_text,
            }

    def _generate_sync(self, prompt: str) -> str:
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
        )

        text = getattr(response, "text", None)
        return text or ""

    def _classify_error(self, error_text: str) -> str:
        text = error_text.lower()

        if "resource_exhausted" in text or "quota exceeded" in text or "429" in text:
            return "quota_exceeded"

        if "permission" in text or "api key" in text or "unauthenticated" in text:
            return "auth_error"

        if "timeout" in text:
            return "timeout"

        if "rate" in text and "limit" in text:
            return "rate_limited"

        return "unknown_error"

    def _extract_retry_after_seconds(self, error_text: str) -> int | None:
        patterns = [
            r"retry in\s+([0-9]+(?:\.[0-9]+)?)s",
            r"retryDelay['\"]?\s*:\s*['\"]?([0-9]+)s",
            r"retryDelay.*?([0-9]+)s",
        ]

        for pattern in patterns:
            match = re.search(pattern, error_text, flags=re.IGNORECASE)
            if match:
                try:
                    return int(float(match.group(1)))
                except Exception:
                    return None

        return None

    def _short_error_message(self, error_type: str, error_text: str) -> str:
        if error_type == "quota_exceeded":
            return "Gemini quota exceeded"

        if error_type == "rate_limited":
            return "Gemini rate limited"

        if error_type == "auth_error":
            return "Gemini authentication/configuration error"

        if error_type == "timeout":
            return "Gemini timeout"

        # Giữ ngắn để log/dashboard không bị quá dài.
        return error_text[:300]