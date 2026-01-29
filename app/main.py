import uuid
import structlog
from time import time
from contextlib import asynccontextmanager
from contextvars import ContextVar
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.core.custom_logging import register_exceptions_handlers
from app.features.extraction.router import router as extraction_router
from app.features.rag.providers.qdrant_client import get_qdrant_store, QdrantStore
from app.features.rag.router import router as rag_router
from app.core.custom_logging import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Iniciando APP")
    print("Verificando colección")
    rag_client: QdrantStore = get_qdrant_store()
    rag_client.create_collection()
    yield


app = FastAPI(lifespan=lifespan)


origins = [
    "http://localhost",
    "http://localhost:8000",
    "http://localhost:8080",
    "*",
    "http://127.0.0.1:8080",
    "http://127.0.0.1:5500",
    "http://localhost:5500",
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

register_exceptions_handlers(app)

request_id_var: ContextVar[str] = ContextVar("request_id", default=None)


@app.middleware("http")
async def structured_log_middleware(request: Request, call_next):
    # Clean previous context
    structlog.contextvars.clear_contextvars()

    # Create and set request_id
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

    token = request_id_var.set(request_id)

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

        response.headers["X-Request-ID"] = request_id

        return response

    except Exception as exc:
        log = structlog.get_logger()
        log.error(
            "request_failed",
            exc_mesg=str(exc),
        )
        raise exc

    finally:
        request_id_var.reset(token)
