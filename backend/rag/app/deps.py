"""FastAPI dependencies."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Request

from rag.pipeline import RagPipeline
from services.rag_service import RagService


def get_pipeline(request: Request) -> RagPipeline:
    pipeline = getattr(request.app.state, "pipeline", None)
    if pipeline is None:
        raise HTTPException(status_code=503, detail="RAG pipeline is not initialized")
    return pipeline


def get_rag_service(request: Request) -> RagService:
    svc = getattr(request.app.state, "rag_service", None)
    if svc is None:
        raise HTTPException(status_code=503, detail="RAG service is not initialized")
    return svc


PipelineDep = Annotated[RagPipeline, Depends(get_pipeline)]
RagServiceDep = Annotated[RagService, Depends(get_rag_service)]
