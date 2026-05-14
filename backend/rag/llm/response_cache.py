import hashlib
import json
import logging
from pathlib import Path
from typing import Any

from core.config import settings
from core.redis_client import get_redis

logger = logging.getLogger(__name__)


class ResponseCache:
    """Gemini answer cache: Redis when REDIS_URL is set, else JSONL + in-memory."""

    def __init__(self) -> None:
        self._redis = get_redis()
        self._key_prefix = settings.redis_key_prefix.rstrip(":") + ":"
        self._ttl = max(60, int(settings.gemini_response_cache_ttl_seconds))

        self.cache_dir = settings.root_dir / "data" / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "gemini_response_cache.jsonl"
        self._cache: dict[str, dict[str, Any]] = {}

        if self._redis is None:
            self._load()

    def _redis_record_key(self, cache_key: str) -> str:
        return f"{self._key_prefix}gem:v1:{cache_key}"

    def _load(self) -> None:
        self._cache = {}

        if not self.cache_file.exists():
            return

        for line in self.cache_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue

            try:
                record = json.loads(line)
                key = record.get("cache_key")
                if key:
                    self._cache[key] = record
            except Exception:
                continue

    def make_key(
        self,
        query: str,
        runtime_mode: str,
        model_name: str,
        place_ids: list[str],
    ) -> str:
        payload = {
            "query": query.strip().lower(),
            "runtime_mode": runtime_mode,
            "model_name": model_name,
            "place_ids": place_ids,
        }

        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def get(self, cache_key: str) -> dict[str, Any] | None:
        if self._redis is not None:
            try:
                raw = self._redis.get(self._redis_record_key(cache_key))
                if not raw:
                    return None
                return json.loads(raw)
            except Exception as exc:
                logger.warning("Redis cache get failed: %s", exc)
                return None

        return self._cache.get(cache_key)

    def set(self, cache_key: str, record: dict[str, Any]) -> None:
        record = dict(record)
        record["cache_key"] = cache_key

        if self._redis is not None:
            try:
                self._redis.setex(
                    self._redis_record_key(cache_key),
                    self._ttl,
                    json.dumps(record, ensure_ascii=False),
                )
            except Exception as exc:
                logger.warning("Redis cache set failed: %s", exc)
            return

        self._cache[cache_key] = record

        with self.cache_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def status(self) -> dict[str, Any]:
        if self._redis is not None:
            return {
                "enabled": True,
                "backend": "redis",
                "key_prefix": self._key_prefix,
                "ttl_seconds": self._ttl,
                "redis_url_configured": bool(settings.redis_url),
            }

        file_exists = self.cache_file.exists()
        file_size_bytes = self.cache_file.stat().st_size if file_exists else 0

        return {
            "enabled": True,
            "backend": "local_jsonl",
            "cache_file": str(self.cache_file),
            "file_exists": file_exists,
            "records_in_memory": len(self._cache),
            "file_size_bytes": file_size_bytes,
        }

    def clear(self) -> dict[str, Any]:
        if self._redis is not None:
            pattern = f"{self._key_prefix}gem:v1:*"
            deleted = 0
            cursor = 0
            try:
                while True:
                    cursor, keys = self._redis.scan(cursor=cursor, match=pattern, count=500)
                    if keys:
                        deleted += int(self._redis.delete(*keys))
                    if cursor == 0:
                        break
            except Exception as exc:
                logger.warning("Redis cache clear failed: %s", exc)
                return {"cleared": False, "backend": "redis", "error": str(exc)}

            return {"cleared": True, "backend": "redis", "keys_deleted": deleted}

        old_count = len(self._cache)
        self._cache = {}

        if self.cache_file.exists():
            self.cache_file.unlink()

        return {
            "cleared": True,
            "backend": "local_jsonl",
            "old_records": old_count,
            "cache_file": str(self.cache_file),
        }

    def reload(self) -> dict[str, Any]:
        if self._redis is None:
            self._load()
        return self.status()
