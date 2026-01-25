import inspect
import time
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging
import structlog
from structlog.processors import (
    JSONRenderer,
    StackInfoRenderer,
    dict_tracebacks,
    add_log_level,
    TimeStamper,
)
from structlog.dev import ConsoleRenderer
from functools import wraps
import sys

from structlog.stdlib import LoggerFactory


def configure_structlog(is_production: bool = False):
    shared_processors = [
        StackInfoRenderer(),
        dict_tracebacks,
        add_log_level,
        TimeStamper(fmt="iso", utc=True),
    ]

    if is_production:
        processors = shared_processors + [JSONRenderer]

    else:
        processors = shared_processors + [ConsoleRenderer(colors=True)]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)


configure_structlog(is_production=False)

logger = structlog.get_logger()


def register_exceptions_handlers(app):
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        logger.warning("http_error", detail=exc.detail, path=str(request.url))

        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        logger.error(
            "validation_error", detail=str(exc.errors()), path=str(request.url)
        )
        return JSONResponse(
            status_code=422,
            content={"detail": exc.errors()},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.error("unhandled_error", path=str(request.url), error=str(exc))
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal Server Error"},
        )


def time_response(func):
    if inspect.iscoroutinefunction(func):

        @wraps(func)
        async def wrapper_async(*args, **kwargs):
            start_time = time.perf_counter()

            resultado = await func(*args, **kwargs)

            duration = time.perf_counter() - start_time

            logger.info(func.__name__, duration=f"{duration:.3f}s")

            return resultado

        return wrapper_async

    else:

        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.perf_counter()

            resultado = func(*args, **kwargs)

            duration = time.perf_counter() - start_time

            logger.info(func.__name__, duration=f"{duration:.3f}s")

            return resultado

        return wrapper
