import os
import uuid
import asyncio
import structlog
from time import time
from contextlib import asynccontextmanager
from contextvars import ContextVar
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from .infrastructure.logging import register_exceptions_handlers, logger
from .infrastructure.metrics import http_requests_total, registry
from .api.extraction.router import router as extraction_router
from .infrastructure.storage.qdrant_client import get_qdrant_store
from .api.rag.router import router as rag_router
from .api.llamaindex.router import router as llama_router
from .api.agent.router import router as agent_router
from prometheus_client import make_asgi_app


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("starting_application", phase="startup")

    # Run sync Qdrant operation in thread pool to avoid blocking event loop
    rag_client = await asyncio.to_thread(get_qdrant_store)
    await asyncio.to_thread(rag_client.create_collection)

    logger.info("application_ready", phase="startup_complete")
    yield
    logger.info("shutdown_application", phase="shutdown")


app = FastAPI(lifespan=lifespan)


# CORS origins from environment variable (comma-separated)
# Default to localhost only in development
DEFAULT_ORIGINS = "http://localhost:8000,http://localhost:8080,http://localhost:5173"
origins = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", DEFAULT_ORIGINS).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(extraction_router)
app.include_router(rag_router)
app.include_router(llama_router)
app.include_router(agent_router)

metrics_app = make_asgi_app(registry)

app.mount("/metrics", metrics_app)

register_exceptions_handlers(app)

request_id_var: ContextVar[str] = ContextVar("request_id", default=None)
session_id_var: ContextVar[str] = ContextVar("session_id", default=None)


@app.middleware("http")
async def structured_log_middleware(request: Request, call_next):
    # Clean previous context
    structlog.contextvars.clear_contextvars()

    # Create and set request_id and session_id
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    session_id = request.headers.get("X-Session-ID") or str(uuid.uuid4())

    token = request_id_var.set(request_id)
    session = session_id_var.set(session_id)

    request.state.request_id = request_id
    request.state.session_id = session_id

    start_time = time()

    structlog.contextvars.bind_contextvars(
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        client_ip=request.client.host if request.client else "unknown",
        session_id=session_id,
    )

    try:
        response = await call_next(request)
        duration = time() - start_time
        user = request.state.user if hasattr(request.state, "user") else "anonymous"

        logger.info(
            f"method={request.method} path={request.url.path} user={user} duration={duration:.3f}s status={response.status_code}"
        )

        http_requests_total.labels(
            request.method, request.url.path, response.status_code
        ).inc()

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Session-ID"] = session_id

        return response

    except Exception as exc:
        log = structlog.get_logger()
        log.error(
            "request_failed",
            exc_mesg=str(exc),
        )
        http_requests_total.labels(request.method, request.url.path, 500).inc()
        raise exc

    finally:
        request_id_var.reset(token)
        session_id_var.reset(session)
