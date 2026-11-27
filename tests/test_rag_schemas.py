"""Pure Pydantic contract tests for RAG request, response, and error schemas."""

import pytest
from pydantic import ValidationError

from app.api.retrieval_engine.jobs.schemas import JobStatus
from app.api.retrieval_engine.schemas.query import Citation, Metadata, QueryRequest
from app.api.retrieval_engine.schemas.request import IngestRequest
from app.api.retrieval_engine.schemas.response import (
    DeleteDocumentResponse,
    ErrorResponse,
    IngestJobResponse,
    JobStatusResponse,
    SourceMetadata,
)


@pytest.mark.parametrize(
    ("field", "value", "expected"),
    [
        ("domain", "  Python  ", "python"),
        ("topic", " Machine Learning ", "machine learning"),
        ("domain", "RAG", "rag"),
        ("topic", None, None),
        ("domain", "", ""),
    ],
)
def test_query_request_normalizes_filters(
    field: str, value: str | None, expected: str | None
) -> None:
    request = QueryRequest(text="valid text", **{field: value})

    assert getattr(request, field) == expected


def test_query_request_rejects_short_text() -> None:
    with pytest.raises(ValidationError):
        QueryRequest(text="abc")


def test_query_request_rejects_long_text() -> None:
    with pytest.raises(ValidationError):
        QueryRequest(text="a" * 1001)


def test_query_request_rejects_long_domain() -> None:
    with pytest.raises(ValidationError):
        QueryRequest(text="valid text", domain="a" * 51)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("domain", "   "),
        ("topic", "\t \n"),
    ],
)
def test_ingest_request_rejects_blank_filters(field: str, value: str) -> None:
    with pytest.raises(ValidationError, match=f"{field} must not be blank"):
        IngestRequest(url="https://example.com/doc", **{field: value})


def test_ingest_request_normalizes_nonblank_filters() -> None:
    request = IngestRequest(
        url="https://example.com/doc",
        domain="  Python  ",
        topic=" Machine Learning ",
    )

    assert (request.domain, request.topic) == ("python", "machine learning")


def test_citation_rejects_negative_chunk_index() -> None:
    with pytest.raises(ValidationError):
        Citation(source="a.pdf", chunk_index=-1, text="chunk")


def test_metadata_rejects_negative_tokens() -> None:
    with pytest.raises(ValidationError):
        Metadata(tokens=-1, cost=0.0)


def test_metadata_rejects_negative_cost() -> None:
    with pytest.raises(ValidationError):
        Metadata(tokens=0, cost=-0.1)


def test_error_response_retryable_defaults_to_false() -> None:
    response = ErrorResponse(code="bad_request", message="bad request")

    assert response.retryable is False


def test_ingest_job_response_rejects_invalid_status_literal() -> None:
    with pytest.raises(ValidationError):
        IngestJobResponse(status="done", job_id="job-1")


def test_job_status_response_accepts_enum_value() -> None:
    response = JobStatusResponse(
        job_id="job-1", status=JobStatus.completed, step="done"
    )

    assert response.status is JobStatus.completed


def test_job_status_response_rejects_unknown_status() -> None:
    with pytest.raises(ValidationError):
        JobStatusResponse(job_id="job-1", status="unknown", step="done")


def test_delete_document_response_rejects_invalid_status_literal() -> None:
    with pytest.raises(ValidationError):
        DeleteDocumentResponse(status="success", source="a.pdf")


def test_ingest_request_accepts_replaces_source() -> None:
    request = IngestRequest(
        url="https://example.com/docs", replaces_source="pdf:old"
    )

    assert request.replaces_source == "pdf:old"


def test_source_metadata_display_name_is_optional() -> None:
    metadata = SourceMetadata(
        source="a.pdf", domain="python", topic="rag", chunk_count=1, last_ingested=0
    )

    assert metadata.display_name is None
