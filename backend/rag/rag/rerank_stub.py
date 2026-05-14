"""Optional cross-encoder rerank (stub for future sentence-transformers / API rerank)."""

from __future__ import annotations

from typing import Any


def maybe_cross_encoder_rerank(
    query: str,
    items: list[dict[str, Any]],
    *,
    top_k: int,
    enabled: bool = False,
) -> list[dict[str, Any]]:
    if not enabled or not items:
        return items[:top_k]
    return items[:top_k]
