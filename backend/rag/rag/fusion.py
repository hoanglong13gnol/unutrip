"""Rank fusion helpers (RRF)."""

from __future__ import annotations

from typing import Hashable


def reciprocal_rank_fusion(
    ranked_lists: list[list[Hashable]],
    k: float = 60.0,
) -> dict[Hashable, float]:
    """
    Classic RRF: score(d) = sum_i 1 / (k + rank_i(d)).
    Missing documents in a list are ignored for that list.
    """
    scores: dict[Hashable, float] = {}
    for ranked in ranked_lists:
        for rank, doc_id in enumerate(ranked, start=1):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + float(rank))
    return scores
