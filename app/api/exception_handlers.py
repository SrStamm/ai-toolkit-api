"""Exception handlers that render all API errors with ErrorResponse."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.exceptions import ApiError
from app.api.retrieval_engine.schemas.response import ErrorResponse
from app.infrastructure.logging import logger

HTTP_ERROR_CODES: dict[int, str] = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    422: "validation_error",
}


def register_exceptions_handlers(app: FastAPI) -> None:
    """Register handlers that convert exceptions into ErrorResponse bodies."""

    @app.exception_handler(ApiError)
    async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
        logger.warning(
            "api_error",
            detail=exc.message,
            code=exc.code,
            status_code=exc.status_code,
            path=str(request.url),
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                code=exc.code,
                message=exc.message,
                retryable=exc.retryable,
            ).model_dump(),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        logger.warning("http_error", detail=exc.detail, path=str(request.url))
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                code=HTTP_ERROR_CODES.get(exc.status_code, "http_error"),
                message=str(exc.detail),
                retryable=False,
            ).model_dump(),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        logger.error(
            "validation_error", detail=str(exc.errors()), path=str(request.url)
        )
        return JSONResponse(
            status_code=422,
            content=ErrorResponse(
                code="validation_error",
                message=str(exc.errors()),
                retryable=False,
            ).model_dump(),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.error("unhandled_error", path=str(request.url), error=str(exc))
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                code="internal_error",
                message="Internal Server Error",
                retryable=False,
            ).model_dump(),
        )
