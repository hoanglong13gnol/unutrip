"""Rate limit for /rag/* and /ai/* — Redis fixed window when REDIS_URL set, else in-memory sliding."""

from __future__ import annotations

import time
from collections import defaultdict, deque

from starlette.concurrency import run_in_threadpool
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from core.config import settings
from core.rate_limit_redis import fixed_window_allow


class RagRateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, per_minute: int) -> None:
        super().__init__(app)
        self.per_minute = per_minute
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def _is_rate_limited_path(self, path: str) -> bool:
        if path.startswith("/rag/"):
            return True
        if path.startswith("/v1/rag/"):
            return True
        if path.startswith("/ai/"):
            return True
        if path.startswith("/v1/ai/"):
            return True
        return False

    def _memory_sliding_allow(self, ip: str) -> bool:
        now = time.monotonic()
        window = 60.0
        dq = self._hits[ip]
        while dq and dq[0] < now - window:
            dq.popleft()

        if len(dq) >= self.per_minute:
            return False

        dq.append(now)
        return True

    async def dispatch(self, request: Request, call_next):
        if self.per_minute <= 0:
            return await call_next(request)

        if request.method == "OPTIONS":
            return await call_next(request)

        path = request.url.path
        if not self._is_rate_limited_path(path):
            return await call_next(request)

        ip = request.client.host if request.client else "unknown"
        redis_client = getattr(request.app.state, "redis_client", None)

        if redis_client is not None:
            key = f"{settings.redis_key_prefix.rstrip(':')}:rl:{ip}"
            allowed = await run_in_threadpool(
                fixed_window_allow,
                redis_client,
                key,
                self.per_minute,
                60,
            )
        else:
            allowed = self._memory_sliding_allow(ip)

        if not allowed:
            rid = getattr(request.state, "request_id", None)
            return JSONResponse(
                {
                    "success": False,
                    "error": "rate_limited",
                    "detail": "Too many AI/RAG requests; retry shortly.",
                    "request_id": rid,
                },
                status_code=429,
            )

        return await call_next(request)
