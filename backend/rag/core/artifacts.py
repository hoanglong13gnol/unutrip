"""Versioned RAG artifact manifest (corpus + index checksums)."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.config import settings

MANIFEST_NAME = "rag_artifacts_manifest.json"


def manifest_path() -> Path:
    return settings.indexes_dir / MANIFEST_NAME


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def load_manifest() -> dict[str, Any] | None:
    path = manifest_path()
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def write_manifest(
    *,
    corpus_path: Path,
    corpus_sha256: str,
    bm25_index_path: Path,
    bm25_sha256: str,
    document_count: int,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    settings.indexes_dir.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "schema_version": 1,
        "built_at_utc": datetime.now(timezone.utc).isoformat(),
        "api_version": settings.api_version,
        "corpus_path": str(corpus_path),
        "corpus_sha256": corpus_sha256,
        "bm25_index_path": str(bm25_index_path),
        "bm25_sha256": bm25_sha256,
        "document_count": document_count,
        "tfidf_enabled": bool(extra and extra.get("tfidf_enabled")),
    }
    if extra:
        for key, value in extra.items():
            if key not in payload:
                payload[key] = value
    manifest_path().write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def manifest_status_block() -> dict[str, Any]:
    m = load_manifest()
    if not m:
        return {"present": False}
    return {
        "present": True,
        "built_at_utc": m.get("built_at_utc"),
        "api_version": m.get("api_version"),
        "corpus_sha256": m.get("corpus_sha256"),
        "bm25_sha256": m.get("bm25_sha256"),
        "document_count": m.get("document_count"),
        "tfidf_enabled": m.get("tfidf_enabled"),
        "corpus_path": m.get("corpus_path"),
    }
