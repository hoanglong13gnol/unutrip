from typing import Any, Optional, Literal
from pydantic import BaseModel, Field


class UserIntent(BaseModel):
    intent: Literal["chat", "search_place", "itinerary", "compare", "unknown"] = "chat"
    query: str

    province: Optional[str] = None
    city: Optional[str] = None
    area: Optional[str] = None

    days: Optional[int] = None
    time_slot: Optional[Literal["morning", "afternoon", "evening", "night", "full_day"]] = None

    budget_level: Optional[Literal["free", "low", "medium", "high", "luxury"]] = None

    has_children: bool = False
    has_elderly: bool = False

    walking_preference: Optional[Literal["easy", "moderate", "hard"]] = None
    activity_preference: Optional[Literal["light", "moderate", "active"]] = None

    interests: list[str] = Field(default_factory=list)
    avoid: list[str] = Field(default_factory=list)


class RetrievedPlace(BaseModel):
    place_id: str
    name: str
    province: Optional[str] = None
    city: Optional[str] = None
    area: Optional[str] = None

    category_main: Optional[str] = None
    category_sub: Optional[str] = None
    short_description: Optional[str] = None

    quality_score: Optional[float] = None
    final_score: float = 0.0
    reason: str = ""

    requires_realtime_check: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class RagRequest(BaseModel):
    message: str
    mode: Literal["fast", "balanced", "max_power"] = "balanced"

    province: Optional[str] = None
    city: Optional[str] = None
    days: Optional[int] = None
    budget_level: Optional[str] = None

    has_children: bool = False
    has_elderly: bool = False

    interests: list[str] = Field(default_factory=list)


class RagResponse(BaseModel):
    answer: str
    rag_mode: str
    model_used: str = "none"
    fallback_used: bool = False

    places: list[RetrievedPlace] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    latency_ms: dict[str, float] = Field(default_factory=dict)
    debug: dict[str, Any] = Field(default_factory=dict)