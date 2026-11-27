import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.api.exception_handlers import register_exceptions_handlers
from app.api.exceptions import ApiError

EXPECTED_HTTP_ERROR_CODES: list[tuple[int, str]] = [
    (400, "bad_request"),
    (401, "unauthorized"),
    (403, "forbidden"),
    (404, "not_found"),
    (405, "method_not_allowed"),
    (409, "conflict"),
    (422, "validation_error"),
    (500, "http_error"),
]


@pytest.fixture
def error_client():
    app = FastAPI()
    register_exceptions_handlers(app)

    @app.get("/api-error")
    def api_error():
        raise ApiError(503, "vector_store_error", "VectorStore unavailable", retryable=True)

    @app.get("/boom")
    def boom():
        raise RuntimeError("no debe filtrarse")

    @app.get("/http-error/{status_code}")
    def http_error(status_code: int):
        raise HTTPException(status_code=status_code, detail="boom")

    @app.get("/validation-error")
    def validation_error(limit: int):
        return {"limit": limit}

    return TestClient(app, raise_server_exceptions=False)

def test_api_error_uses_error_response_envelope(error_client):
    response = error_client.get("/api-error")

    assert response.json() == {
        "code": "vector_store_error",
        "message": "VectorStore unavailable",
        "retryable": True,
    }


def test_api_error_returns_status_code(error_client: TestClient) -> None:
    response = error_client.get("/api-error")

    assert response.status_code == 503


@pytest.mark.parametrize(
    ("status_code", "expected_code"), EXPECTED_HTTP_ERROR_CODES
)
def test_http_error_uses_mapped_code(
    error_client: TestClient, status_code: int, expected_code: str
) -> None:
    response = error_client.get(f"/http-error/{status_code}")

    assert response.json()["code"] == expected_code


@pytest.mark.parametrize(
    "status_code", [code for code, _ in EXPECTED_HTTP_ERROR_CODES]
)
def test_http_error_preserves_status_code(
    error_client: TestClient, status_code: int
) -> None:
    response = error_client.get(f"/http-error/{status_code}")

    assert response.status_code == status_code


def test_validation_error_returns_status_422(error_client: TestClient) -> None:
    response = error_client.get("/validation-error?limit=abc")

    assert response.status_code == 422


def test_validation_error_uses_validation_error_code(
    error_client: TestClient,
) -> None:
    response = error_client.get("/validation-error?limit=abc")

    assert response.json()["code"] == "validation_error"


def test_validation_error_message_is_a_string(error_client: TestClient) -> None:
    response = error_client.get("/validation-error?limit=abc")

    assert isinstance(response.json()["message"], str)
    assert "limit" in response.json()["message"]


def test_unhandled_error_returns_status_500(error_client: TestClient) -> None:
    response = error_client.get("/boom")

    assert response.status_code == 500


def test_unhandled_error_uses_internal_error_code(error_client: TestClient) -> None:
    response = error_client.get("/boom")

    assert response.json()["code"] == "internal_error"


def test_unhandled_error_uses_generic_message(error_client: TestClient) -> None:
    response = error_client.get("/boom")

    assert response.json()["message"] == "Internal Server Error"


def test_unhandled_error_does_not_leak_exception_text(
    error_client: TestClient,
) -> None:
    response = error_client.get("/boom")

    assert "no debe filtrarse" not in response.text
