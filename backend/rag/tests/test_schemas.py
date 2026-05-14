"""Contract tests for HTTP request schemas (no network, no indexes)."""

import pytest
from pydantic import ValidationError

from app.schemas import RagChatRequest, RagChatSimpleRequest, RagRetrieveRequest


def test_rag_chat_request_top_k_upper_bound() -> None:
    RagChatRequest(message="x", top_k=12)
    with pytest.raises(ValidationError):
        RagChatRequest(message="x", top_k=13)


def test_rag_chat_simple_top_k_bounds() -> None:
    RagChatSimpleRequest(message="x", top_k=10)
    with pytest.raises(ValidationError):
        RagChatSimpleRequest(message="x", top_k=11)


def test_rag_retrieve_top_k_bounds() -> None:
    RagRetrieveRequest(message="x", top_k=20)
    with pytest.raises(ValidationError):
        RagRetrieveRequest(message="x", top_k=21)


def test_rag_chat_simple_optional_geo() -> None:
    m = RagChatSimpleRequest(
        message="Đà Nẵng có gì chơi?",
        targetProvince="Đà Nẵng",
        targetCity=None,
    )
    assert m.targetProvince == "Đà Nẵng"
    assert m.targetCity is None
