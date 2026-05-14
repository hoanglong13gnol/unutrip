"""Unit tests for rank fusion (no data files)."""

from rag.fusion import reciprocal_rank_fusion


def test_reciprocal_rank_fusion_single_list() -> None:
    scores = reciprocal_rank_fusion([["a", "b", "c"]], k=60.0)
    assert scores["a"] > scores["b"] > scores["c"]


def test_reciprocal_rank_fusion_two_lists_agreement() -> None:
    scores = reciprocal_rank_fusion([["x", "y"], ["y", "x"]], k=60.0)
    assert abs(scores["x"] - scores["y"]) < 1e-9


def test_reciprocal_rank_fusion_boosts_consensus() -> None:
    scores = reciprocal_rank_fusion(
        [
            ["d1", "d2"],
            ["d1", "d3", "d2"],
        ],
        k=60.0,
    )
    assert scores["d1"] > scores["d2"]
    assert scores["d1"] > scores["d3"]
