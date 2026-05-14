"""Optional service-to-service authentication."""

import os


def get_internal_api_key() -> str | None:
    raw = os.getenv("RAG_INTERNAL_API_KEY", "").strip()
    return raw or None


def get_admin_api_key() -> str | None:
    """When set, /admin/* requires this key (or Bearer) instead of the app internal key."""
    raw = os.getenv("RAG_ADMIN_API_KEY", "").strip()
    return raw or None


def get_cors_origins() -> list[str]:
    raw = os.getenv("RAG_CORS_ORIGINS", "").strip()
    if not raw:
        return []
    return [x.strip() for x in raw.split(",") if x.strip()]


def is_debug_mode() -> bool:
    v = os.getenv("RAG_DEBUG", "").strip().lower()
    return v in {"1", "true", "yes", "on"}
