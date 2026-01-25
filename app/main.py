from contextlib import asynccontextmanager
from contextvars import ContextVar
import uuid
from time import time
import structlog
from fastapi import FastAPI, Request
from app.core.custom_logging import register_exceptions_handlers
from app.features.extraction.router import router as extraction_router
from app.features.rag.rag_client import get_rag_client, RAGClient
from app.features.rag.router import router as rag_router
from app.core.custom_logging import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Iniciando APP")
    print("Verificando colección")
    rag_client: RAGClient = get_rag_client()
    rag_client.create_collection()
    yield


app = FastAPI(lifespan=lifespan)

app.include_router(extraction_router)
app.include_router(rag_router)

register_exceptions_handlers(app)

request_id_var: ContextVar[str] = ContextVar("request_id", default=None)


@app.middleware("http")
async def structured_log_middleware(request: Request, call_next):
    # Clean previous context
    structlog.contextvars.clear_contextvars()

    # Create and set request_id
    request_id = str(uuid.uuid4())
    request_id_var.set(request_id)

    start_time = time()

    structlog.contextvars.bind_contextvars(
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        client_ip=request.client.host if request.client else "unknown",
    )

    try:
        response = await call_next(request)
        duration = time() - start_time
        user = request.state.user if hasattr(request.state, "user") else "anonymous"

        # Use request.url.scheme instead of request.scope["scheme"]
        scheme = request.url.scheme or "http"  # Fallback to 'http' if scheme is empty
        if not scheme:
            logger.warning(f"Invalid scheme in request URL: {request.url}")

        logger.info(
            f"method={request.method} path={request.url.path} user={user} duration={duration:.3f}s status={response.status_code}"
        )

        return response

    except Exception as exc:
        log = structlog.get_logger()
        log.error(
            "request_failed",
            exc_info=str(exc),
            status_code=500,
        )
        raise
