"""HTTP middleware: request IDs, optional internal API key, CORS."""

import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from core.security import get_cors_origins, get_internal_api_key


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = rid
        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        return response


def _path_exempt_from_api_key(path: str) -> bool:
    if path in {"/health", "/health/ready", "/openapi.json", "/redoc", "/favicon.ico"}:
        return True
    if path.startswith("/docs"):
        return True
    return False


class InternalApiKeyMiddleware(BaseHTTPMiddleware):
    """When RAG_INTERNAL_API_KEY is set, require X-RAG-Internal-Key or Authorization: Bearer <key>."""

    async def dispatch(self, request: Request, call_next):
        key = get_internal_api_key()
        if not key:
            return await call_next(request)

        if request.method == "OPTIONS":
            return await call_next(request)

        path = request.url.path
        if _path_exempt_from_api_key(path):
            return await call_next(request)

        header_key = (request.headers.get("X-RAG-Internal-Key") or "").strip()
        auth = request.headers.get("Authorization") or ""
        bearer = auth[7:].strip() if auth.startswith("Bearer ") else ""
        token = header_key or bearer

        if token != key:
            rid = getattr(request.state, "request_id", None)
            return JSONResponse(
                {
                    "success": False,
                    "error": "unauthorized",
                    "detail": "Invalid or missing RAG internal API key",
                    "request_id": rid,
                },
                status_code=401,
            )

        return await call_next(request)


def attach_cors(app) -> None:
    origins = get_cors_origins()
    if not origins:
        return

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )
