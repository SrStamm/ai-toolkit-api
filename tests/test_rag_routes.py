"""HTTP contract tests for the RAG router and its error envelope."""

from pathlib import Path
from unittest.mock import MagicMock
from urllib.parse import quote

from fastapi.testclient import TestClient

from app.api.retrieval_engine.exceptions import InvalidFilterError, VectorStoreError
from app.domain.source_identity import make_pdf_source
from tests.conftest import FakeVectorStore


def test_delete_document_translates_invalid_filter(
    api_client: TestClient, fake_vector_store: FakeVectorStore
) -> None:
    fake_vector_store.delete_error = InvalidFilterError("bad filter")

    response = api_client.delete("/rag/documents/a.pdf")

    assert response.status_code == 400


def test_delete_document_invalid_filter_code(
    api_client: TestClient, fake_vector_store: FakeVectorStore
) -> None:
    fake_vector_store.delete_error = InvalidFilterError("bad filter")

    response = api_client.delete("/rag/documents/a.pdf")

    assert response.json()["code"] == "invalid_filter"


def test_delete_document_invalid_filter_is_not_retryable(
    api_client: TestClient, fake_vector_store: FakeVectorStore
) -> None:
    fake_vector_store.delete_error = InvalidFilterError("bad filter")

    response = api_client.delete("/rag/documents/a.pdf")

    assert response.json()["retryable"] is False


def test_delete_document_translates_store_failure(
    api_client: TestClient, fake_vector_store: FakeVectorStore
) -> None:
    fake_vector_store.delete_error = VectorStoreError("boom")

    response = api_client.delete("/rag/documents/a.pdf")

    assert response.status_code == 503


def test_delete_document_store_failure_code(
    api_client: TestClient, fake_vector_store: FakeVectorStore
) -> None:
    fake_vector_store.delete_error = VectorStoreError("boom")

    response = api_client.delete("/rag/documents/a.pdf")

    assert response.json()["code"] == "vector_store_error"


def test_delete_document_store_failure_is_retryable(
    api_client: TestClient, fake_vector_store: FakeVectorStore
) -> None:
    fake_vector_store.delete_error = VectorStoreError("boom")

    response = api_client.delete("/rag/documents/a.pdf")

    assert response.json()["retryable"] is True


def test_delete_document_store_failure_message(
    api_client: TestClient, fake_vector_store: FakeVectorStore
) -> None:
    fake_vector_store.delete_error = VectorStoreError("boom")

    response = api_client.delete("/rag/documents/a.pdf")

    assert response.json()["message"] == "Vector store unavailable"


def test_delete_document_returns_success_status(
    api_client: TestClient,
) -> None:
    response = api_client.delete("/rag/documents/a.pdf")

    assert response.status_code == 200
    assert response.json()["status"] == "deleted"


def test_delete_document_uses_source_filter(
    api_client: TestClient, fake_vector_store: FakeVectorStore
) -> None:
    api_client.delete("/rag/documents/a.pdf")

    assert fake_vector_store.deleted_filters == [{"source": "a.pdf"}]


def test_get_document_metadata_missing_returns_404(
    api_client: TestClient,
) -> None:
    response = api_client.get("/rag/documents/metadata?source=missing")

    assert response.status_code == 404


def test_get_document_metadata_missing_code(
    api_client: TestClient,
) -> None:
    response = api_client.get("/rag/documents/metadata?source=missing")

    assert response.json()["code"] == "document_not_found"


def test_get_job_status_missing_returns_404(api_client: TestClient) -> None:
    response = api_client.get("/rag/job/job-404")

    assert response.status_code == 404


def test_get_job_status_missing_code(api_client: TestClient) -> None:
    response = api_client.get("/rag/job/job-404")

    assert response.json()["code"] == "job_not_found"


def test_ingest_file_rejects_non_pdf(api_client: TestClient) -> None:
    response = api_client.post(
        "/rag/ingest-file/job",
        files={"file": ("notes.txt", b"plain text", "text/plain")},
        data={"domain": "general", "topic": "unknown"},
    )

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_file_type"


def test_ingest_file_queues_pdf_job(
    api_client: TestClient,
    mock_celery_tasks: dict[str, MagicMock],
    patch_upload_path: Path,
) -> None:
    response = api_client.post(
        "/rag/ingest-file/job",
        files={"file": ("doc.pdf", b"%PDF-1.4", "application/pdf")},
        data={"domain": "general", "topic": "unknown"},
    )

    assert response.json()["job_id"] == "job-123"
    mock_celery_tasks["ingest_file_job"].assert_called_once()
    assert (patch_upload_path / "job-123.pdf").is_file()


def test_search_rejects_short_query(api_client: TestClient) -> None:
    response = api_client.post(
        "/rag/search", json={"query": "abc", "top_k": 5}
    )

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


def test_list_documents_returns_zero_count(api_client: TestClient) -> None:
    response = api_client.post("/rag/documents")

    assert response.json()["metadata"]["count"] == 0


def test_list_documents_includes_last_ingested(
    api_client: TestClient, fake_vector_store: FakeVectorStore
) -> None:
    fake_vector_store.sources = [
        {
            "source": "a.pdf",
            "domain": "python",
            "topic": "rag",
            "chunk_count": 3,
            "last_ingested": 1700000000,
        }
    ]

    response = api_client.post("/rag/documents")

    assert response.status_code == 200
    assert response.json()["metadata"]["count"] == 1
    assert response.json()["metadata"]["documents"][0]["last_ingested"] == 1700000000


def test_delete_document_with_slashed_url_matches(api_client: TestClient) -> None:
    response = api_client.delete("/rag/documents/https://example.com/docs/page")

    assert response.status_code == 200


def test_delete_document_uses_canonical_url_filter(
    api_client: TestClient, fake_vector_store: FakeVectorStore
) -> None:
    raw = "HTTPS://Example.COM:443/docs?utm_source=x&b=2&a=1"
    api_client.delete(f"/rag/documents/{quote(raw, safe='')}")

    assert fake_vector_store.deleted_filters[0] == {
        "source": "https://example.com/docs?a=1&b=2"
    }


def test_delete_document_removes_canonical_and_legacy_alias(
    api_client: TestClient, fake_vector_store: FakeVectorStore
) -> None:
    raw = "HTTPS://Example.COM:443/docs"
    api_client.delete(f"/rag/documents/{quote(raw, safe='')}")

    assert fake_vector_store.deleted_filters == [
        {"source": "https://example.com/docs"},
        {"source": raw},
    ]


def test_get_document_metadata_falls_back_to_legacy_alias(
    api_client: TestClient, fake_vector_store: FakeVectorStore
) -> None:
    raw = "HTTPS://Example.COM:443/docs"
    fake_vector_store.metadata = {
        "source": raw,
        "domain": "python",
        "topic": "rag",
        "chunk_count": 2,
        "last_ingested": 5,
    }

    response = api_client.get("/rag/documents/metadata", params={"source": raw})

    assert response.json()["metadata"]["source"] == raw


def test_list_documents_renders_display_name(
    api_client: TestClient, fake_vector_store: FakeVectorStore
) -> None:
    fake_vector_store.sources = [
        {
            "source": "pdf:abc",
            "display_name": "report.pdf",
            "domain": "python",
            "topic": "rag",
            "chunk_count": 3,
            "last_ingested": 1700000000,
        }
    ]

    response = api_client.post("/rag/documents")

    assert response.json()["output"] == (
        "Found 1 document(s):\n- report.pdf (python/rag) - 3 chunks"
    )


def test_ingest_file_queues_content_based_source(
    api_client: TestClient,
    mock_celery_tasks: dict[str, MagicMock],
    patch_upload_path: Path,
) -> None:
    content = b"%PDF-1.4\nunique bytes"
    api_client.post(
        "/rag/ingest-file/job",
        files={"file": ("doc.pdf", content, "application/pdf")},
        data={"domain": "general", "topic": "unknown"},
    )

    assert mock_celery_tasks["ingest_file_job"].call_args.kwargs["source"] == (
        make_pdf_source(content)
    )


def test_ingest_file_queues_filename_as_display_name(
    api_client: TestClient,
    mock_celery_tasks: dict[str, MagicMock],
    patch_upload_path: Path,
) -> None:
    api_client.post(
        "/rag/ingest-file/job",
        files={"file": ("doc.pdf", b"%PDF-1.4", "application/pdf")},
        data={"domain": "general", "topic": "unknown"},
    )

    assert mock_celery_tasks["ingest_file_job"].call_args.kwargs["display_name"] == (
        "doc.pdf"
    )


def test_ingest_file_queues_replaces_source(
    api_client: TestClient,
    mock_celery_tasks: dict[str, MagicMock],
    patch_upload_path: Path,
) -> None:
    api_client.post(
        "/rag/ingest-file/job",
        files={"file": ("edited.pdf", b"%PDF-1.4", "application/pdf")},
        data={
            "domain": "general",
            "topic": "unknown",
            "replaces_source": "pdf:old",
        },
    )

    assert mock_celery_tasks["ingest_file_job"].call_args.kwargs["replaces_source"] == (
        "pdf:old"
    )
