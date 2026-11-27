import inspect
import time
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
