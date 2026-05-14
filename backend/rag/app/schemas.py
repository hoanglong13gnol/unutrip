"""Shared request/response Pydantic models for HTTP layer."""

from pydantic import BaseModel, Field


class RagChatRequest(BaseModel):
    message: str
    mode: str = "balanced"
    top_k: int = Field(default=6, ge=1, le=12)
    include_prompt: bool = False


class RagRetrieveRequest(BaseModel):
    message: str
    top_k: int = Field(default=8, ge=1, le=20)


class RagChatSimpleRequest(BaseModel):
    message: str
    mode: str = "balanced"
    top_k: int = Field(default=5, ge=1, le=10)
    targetProvince: str | None = None
    targetCity: str | None = None


class LegacyLocalChatRequest(BaseModel):
    """Body giống `backend/nodejs/server.py` POST /chat — chỉ có message."""

    message: str


class AdminAiDebugQueryRequest(BaseModel):
    message: str
    mode: str = "balanced"
    top_k: int = Field(default=6, ge=1, le=12)
    include_prompt: bool = False


class AdminRagRetrieveDebugRequest(BaseModel):
    message: str
    top_k: int = Field(default=8, ge=1, le=20)
