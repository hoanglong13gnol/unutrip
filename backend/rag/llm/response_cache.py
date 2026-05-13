import hashlib
import json
from pathlib import Path
from typing import Any

from core.config import settings


class ResponseCache:
    def __init__(self) -> None:
        self.cache_dir = settings.root_dir / "data" / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.cache_file = self.cache_dir / "gemini_response_cache.jsonl"
        self._cache: dict[str, dict[str, Any]] = {}
        self._load()

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
        return self._cache.get(cache_key)

    def set(self, cache_key: str, record: dict[str, Any]) -> None:
        record = dict(record)
        record["cache_key"] = cache_key

        self._cache[cache_key] = record

        with self.cache_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def status(self) -> dict[str, Any]:
        file_exists = self.cache_file.exists()
        file_size_bytes = self.cache_file.stat().st_size if file_exists else 0

        return {
            "enabled": True,
            "cache_file": str(self.cache_file),
            "file_exists": file_exists,
            "records_in_memory": len(self._cache),
            "file_size_bytes": file_size_bytes,
        }

    def clear(self) -> dict[str, Any]:
        old_count = len(self._cache)

        self._cache = {}

        if self.cache_file.exists():
            self.cache_file.unlink()

        return {
            "cleared": True,
            "old_records": old_count,
            "cache_file": str(self.cache_file),
        }

    def reload(self) -> dict[str, Any]:
        self._load()
        return self.status()