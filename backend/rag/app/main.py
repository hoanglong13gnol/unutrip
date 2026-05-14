import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from app.ai_itinerary import router as ai_itinerary_router
from app.middleware import InternalApiKeyMiddleware, RequestIdMiddleware, attach_cors
from app.rate_limit_middleware import RagRateLimitMiddleware
from app.routers import admin as admin_router
from app.routers import health as health_router
from app.routers import rag as rag_router
from core.config import get_log_level, settings
from core.logging_config import configure_logging
from core.redis_client import close_redis, init_redis
from core.security import is_debug_mode
from rag.pipeline import RagPipeline
from services.rag_service import RagService

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(get_log_level(), json_logs=settings.log_json)
    app.state.redis_client = init_redis(settings.redis_url)

    logger.info("Starting RAG pipeline…")
    pipeline = RagPipeline()
    app.state.pipeline = pipeline
    app.state.rag_service = RagService(pipeline)
    logger.info("RAG pipeline ready")

    yield

    logger.info("RAG service shutting down")
    app.state.pipeline = None
    app.state.rag_service = None
    close_redis()
    app.state.redis_client = None


app = FastAPI(
    title="UnuTrip RAG",
    description="Retrieval + generation API for UnuTrip. Set RAG_INTERNAL_API_KEY in production.",
    version=settings.api_version,
    lifespan=lifespan,
)

attach_cors(app)
app.add_middleware(RagRateLimitMiddleware, per_minute=settings.rate_limit_per_minute)
app.add_middleware(InternalApiKeyMiddleware)
app.add_middleware(RequestIdMiddleware)

app.include_router(health_router.router)
app.include_router(rag_router.router)
app.include_router(admin_router.router)
app.include_router(ai_itinerary_router)
app.include_router(ai_itinerary_router, prefix="/v1")

app.include_router(health_router.router, prefix="/v1", tags=["Health v1"])
app.include_router(rag_router.router, prefix="/v1", tags=["RAG v1"])

if os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip():
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor.instrument_app(app)
        logger.info("OpenTelemetry FastAPI instrumentation enabled")
    except Exception as exc:
        logger.warning("OpenTelemetry instrumentation skipped: %s", exc)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    rid = getattr(request.state, "request_id", None)
    detail = exc.detail
    if not isinstance(detail, str):
        detail = str(detail)
    return JSONResponse(
        {"success": False, "error": "http_error", "detail": detail, "request_id": rid},
        status_code=exc.status_code,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    rid = getattr(request.state, "request_id", None)
    return JSONResponse(
        {"success": False, "error": "validation_error", "detail": exc.errors(), "request_id": rid},
        status_code=422,
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error path=%s", request.url.path)
    rid = getattr(request.state, "request_id", None)
    detail = str(exc) if is_debug_mode() else "Internal server error"
    return JSONResponse(
        {"success": False, "error": "internal_error", "detail": detail, "request_id": rid},
        status_code=500,
    )
