"""Public RAG HTTP routes (thin: validation + service delegation)."""

from __future__ import annotations

from fastapi import APIRouter
from starlette.concurrency import run_in_threadpool

from app.deps import RagServiceDep
from app.schemas import LegacyLocalChatRequest, RagChatRequest, RagChatSimpleRequest, RagRetrieveRequest

router = APIRouter(tags=["RAG"])


@router.get("/chat")
def legacy_local_chat_help() -> dict[str, str]:
    """Trình duyệt mở URL là GET; chat thật là POST JSON {\"message\":\"...\"}."""
    return {
        "message": "Đây không phải trang web. Dùng POST với JSON {\"message\": \"...\"} hoặc gọi /rag/chat/simple.",
        "post_path": "/chat",
        "content_type": "application/json",
    }


@router.post("/chat")
async def legacy_local_chat(request: LegacyLocalChatRequest, svc: RagServiceDep):
    """Tương thích Node `AI_MODEL_URL` mặc định `…/chat` và `server.py` cũ — chỉ trả `{answer}`."""
    out = await run_in_threadpool(
        svc.rag_chat_simple,
        request.message,
        6,
        "balanced",
        None,
        None,
    )
    return {"answer": (out or {}).get("answer") or ""}


@router.post("/rag/chat")
async def rag_chat(request: RagChatRequest, svc: RagServiceDep):
    return await run_in_threadpool(
        svc.rag_chat,
        request.message,
        request.top_k,
        request.mode,
        request.include_prompt,
    )


@router.post("/rag/retrieve")
async def rag_retrieve(request: RagRetrieveRequest, svc: RagServiceDep):
    return await run_in_threadpool(
        svc.rag_retrieve,
        request.message,
        request.top_k,
    )


@router.post("/rag/chat/simple")
async def rag_chat_simple(request: RagChatSimpleRequest, svc: RagServiceDep):
    return await run_in_threadpool(
        svc.rag_chat_simple,
        request.message,
        request.top_k,
        request.mode,
        request.targetProvince,
        request.targetCity,
    )
