"""RAG pipeline: province matching must not treat missing metadata as a match."""

from rag.pipeline import RagPipeline


def test_empty_place_metadata_does_not_match_any_province() -> None:
    pipe = RagPipeline.__new__(RagPipeline)
    place = {"title": "Chợ đêm X", "metadata": {}}
    assert pipe._place_matches_province(place, "Hà Giang") is False


def test_place_with_province_matches() -> None:
    pipe = RagPipeline.__new__(RagPipeline)
    place = {"title": "Đèo Mã Pí Lèng", "metadata": {"province": "Hà Giang"}}
    assert pipe._place_matches_province(place, "Hà Giang") is True
