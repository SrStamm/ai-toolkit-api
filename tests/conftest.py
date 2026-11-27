"""
Test configuration and fixtures.
"""

import os
import tempfile
from pathlib import Path

import pytest
from unittest.mock import MagicMock

# Setup prometheus multiprocess environment before any imports
os.environ.setdefault("PROMETHEUS_MULTIPROC_DIR", tempfile.mkdtemp())


@pytest.fixture
def mock_llm_provider():
    """Create a mock LLM provider."""
    provider = MagicMock()
    provider.name = "mock"
    provider.model = "mock-model"
    return provider


@pytest.fixture
def mock_rag_orchestrator():
    """Create a mock RAG orchestrator."""
    orchestrator = MagicMock()
    orchestrator.custom_query.return_value = MagicMock(
        answer="Test answer", citations=[], metadata=MagicMock()
    )
    return orchestrator


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client."""
    client = MagicMock()
    client.generate_content.return_value = MagicMock(
        content='{"answer": "Test response"}',
        usage=MagicMock(prompt_tokens=100, completion_tokens=50, total_tokens=150),
        cost=MagicMock(input_cost=0.001, output_cost=0.002, total_cost=0.003),
        model="test-model",
        provider="test",
    )
    return client


class FakeVectorStore:
    """In-memory vector-store double for RAG route tests."""

    def __init__(
        self,
        sources: list[dict] | None = None,
        metadata: dict | None = None,
        delete_error: Exception | None = None,
    ) -> None:
        self.sources: list[dict] = sources or []
        self.metadata: dict | None = metadata
        self.delete_error: Exception | None = delete_error
        self.deleted_filters: list[dict] = []

    def list_sources(self, domain: str | None = None) -> list[dict]:
        """Return configured sources, optionally narrowed to one domain."""
        if domain is None:
            return list(self.sources)
        return [src for src in self.sources if src.get("domain") == domain]

    def get_source_metadata(self, source: str) -> dict | None:
        """Return configured metadata when it matches the requested source."""
        if self.metadata is None:
            return None
        if self.metadata.get("source") not in (None, source):
            return None
        return dict(self.metadata)

    def delete_by_filter(self, filters: dict) -> None:
        """Record a delete filter and raise the configured error, if any."""
        self.deleted_filters.append(dict(filters))
        if self.delete_error is not None:
            raise self.delete_error


class FakeQueryService:
    """Query double returning a configurable context-and-citations payload."""

    def __init__(self, context_result: tuple[str, list[str]] | None = None) -> None:
        self.context_result: tuple[str, list[str]] = context_result or ("", [])

    def get_context(
        self,
        query: str,
        top_k: int = 5,
        domain: str | None = None,
        topic: str | None = None,
    ) -> tuple[str, list[str]]:
        """Return the configured context and citations."""
        return self.context_result


class FakeRagService:
    """RAG-service double wired to a fake vector store and query service."""

    def __init__(
        self,
        vector_store: FakeVectorStore | None = None,
        query: FakeQueryService | None = None,
        context_result: tuple[str, list[str]] | None = None,
    ) -> None:
        self.vector_store: FakeVectorStore = vector_store or FakeVectorStore()
        self.query: FakeQueryService = query or FakeQueryService(context_result)

    @property
    def context_result(self) -> tuple[str, list[str]]:
        """Return the query double's configured context result."""
        return self.query.context_result

    @context_result.setter
    def context_result(self, value: tuple[str, list[str]]) -> None:
        """Set the query double's context result."""
        self.query.context_result = value


class FakeJobService:
    """Job-service double with in-memory state and no-op mutations."""

    def __init__(self, state: dict | None = None) -> None:
        self.state: dict | None = state

    def create(self) -> str:
        """Return a deterministic job identifier."""
        return "job-123"

    def get_state(self, job_id: str) -> dict:
        """Return configured state or raise ValueError when it is missing."""
        if self.state is None:
            raise ValueError(f"Job {job_id} not found")
        return self.state

    def update_status(self, job_id: str, status: str) -> None:
        """Ignore status updates."""
        return None

    def update_progress(self, job_id: str, progress: int, step: str) -> None:
        """Ignore progress updates."""
        return None

    def fail(self, job_id: str, error: str) -> None:
        """Ignore failures."""
        return None


@pytest.fixture
def fake_vector_store() -> FakeVectorStore:
    """Return an empty in-memory vector-store double."""
    return FakeVectorStore()


@pytest.fixture
def fake_rag_service(fake_vector_store: FakeVectorStore) -> FakeRagService:
    """Return a RAG-service double backed by the fake vector store."""
    return FakeRagService(vector_store=fake_vector_store)


@pytest.fixture
def fake_job_service() -> FakeJobService:
    """Return a job-service double with no stored state."""
    return FakeJobService()


@pytest.fixture
def api_client(
    fake_rag_service: FakeRagService, fake_job_service: FakeJobService
) -> "TestClient":
    """Return an isolated FastAPI client with RAG and job dependencies overridden."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.api.exception_handlers import register_exceptions_handlers
    from app.api.retrieval_engine.jobs.job_service import JobService
    from app.api.retrieval_engine.router import router
    from app.api.retrieval_engine.service import get_rag_service

    app = FastAPI()
    register_exceptions_handlers(app)
    app.include_router(router)
    app.dependency_overrides[get_rag_service] = lambda: fake_rag_service
    app.dependency_overrides[JobService] = lambda: fake_job_service
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def mock_celery_tasks(
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, MagicMock]:
    """Replace both Celery task ``delay`` methods with MagicMock instances."""
    from app.api.retrieval_engine.router import ingest_file_job, ingest_html_job

    file_delay = MagicMock()
    html_delay = MagicMock()
    monkeypatch.setattr(ingest_file_job, "delay", file_delay)
    monkeypatch.setattr(ingest_html_job, "delay", html_delay)
    return {"ingest_file_job": file_delay, "ingest_html_job": html_delay}


@pytest.fixture
def patch_upload_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Path:
    """Redirect the router's hard-coded upload directory to a temporary path."""
    import app.api.retrieval_engine.router as router_module

    def _path_factory(_: str) -> Path:
        """Return the temporary upload root instead of the production path."""
        return tmp_path

    monkeypatch.setattr(router_module, "Path", _path_factory)
    return tmp_path
