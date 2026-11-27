"""Tests for explicit source replacement during ingestion."""

from types import SimpleNamespace
from unittest.mock import ANY, AsyncMock, MagicMock, call

import pytest

from app.api.extraction.schema import ChunkWithMetadata
from app.api.retrieval_engine.exceptions import ChunkingError
from app.api.retrieval_engine.ingestion_service import IngestionService


@pytest.fixture
def vector_store() -> MagicMock:
    """Return a vector store double that records calls without I/O."""
    store = MagicMock()
    store.retrieve.return_value = []
    store.create_point.side_effect = lambda hash_id, vector, payload: SimpleNamespace(
        id=hash_id, vector=vector, payload=payload
    )
    return store


@pytest.fixture
def embed_service() -> MagicMock:
    """Return an embedding double producing deterministic vectors."""
    service = MagicMock()
    service.batch_embed.return_value = [
        SimpleNamespace(dense=[0.1], sparse={"indices": [1], "values": [0.2]})
    ]
    return service


@pytest.fixture
def ingestion_service(
    vector_store: MagicMock, embed_service: MagicMock
) -> IngestionService:
    """Return an ingestion service wired to the doubles."""
    return IngestionService(vector_store=vector_store, embed_service=embed_service)


@pytest.mark.asyncio
async def test_replacement_delete_precedes_insert(
    ingestion_service: IngestionService, vector_store: MagicMock
) -> None:
    events = MagicMock()
    events.attach_mock(vector_store.delete_by_filter, "delete_by_filter")
    events.attach_mock(vector_store.insert_vector, "insert_vector")

    await ingestion_service._process_ingestion(
        chunks=[ChunkWithMetadata(text="new content", section=None)],
        source="pdf:new",
        domain="python",
        topic="rag",
        display_name="new.pdf",
        replaces_source="pdf:old",
    )

    assert events.mock_calls == [
        call.delete_by_filter({"source": "pdf:old"}),
        call.insert_vector(ANY),
    ]


@pytest.mark.asyncio
async def test_same_source_replacement_skips_delete(
    ingestion_service: IngestionService, vector_store: MagicMock
) -> None:
    await ingestion_service._process_ingestion(
        chunks=[ChunkWithMetadata(text="new content", section=None)],
        source="pdf:same",
        domain="python",
        topic="rag",
        replaces_source="pdf:same",
    )

    assert vector_store.delete_by_filter.call_count == 0


@pytest.mark.asyncio
async def test_new_points_carry_display_name(
    ingestion_service: IngestionService, vector_store: MagicMock
) -> None:
    await ingestion_service._process_ingestion(
        chunks=[ChunkWithMetadata(text="new content", section=None)],
        source="pdf:new",
        domain="python",
        topic="rag",
        display_name="edited.pdf",
    )

    assert vector_store.create_point.call_args.kwargs["payload"]["display_name"] == (
        "edited.pdf"
    )


@pytest.mark.asyncio
async def test_display_name_falls_back_to_source(
    ingestion_service: IngestionService, vector_store: MagicMock
) -> None:
    await ingestion_service._process_ingestion(
        chunks=[ChunkWithMetadata(text="new content", section=None)],
        source="pdf:new",
        domain="python",
        topic="rag",
    )

    assert vector_store.create_point.call_args.kwargs["payload"]["display_name"] == (
        "pdf:new"
    )


@pytest.mark.asyncio
async def test_updated_points_keep_existing_display_name(
    ingestion_service: IngestionService, vector_store: MagicMock
) -> None:
    chunk = ChunkWithMetadata(text="existing content", section=None)
    chunk_id = ingestion_service._generate_deterministic_ids([chunk], "pdf:new")[0]
    vector_store.retrieve.return_value = [
        SimpleNamespace(
            id=chunk_id,
            vector={"dense": [0.1], "sparse": {}},
            payload={"text": chunk.text, "display_name": "old.pdf"},
        )
    ]

    await ingestion_service._process_ingestion(
        chunks=[chunk],
        source="pdf:new",
        domain="python",
        topic="rag",
    )

    assert vector_store.create_point.call_args.kwargs["payload"]["display_name"] == (
        "old.pdf"
    )


@pytest.mark.asyncio
async def test_validation_failure_leaves_old_source_untouched(
    ingestion_service: IngestionService,
    vector_store: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    extractor = MagicMock()
    extractor.extract = AsyncMock(return_value="extracted text")
    cleaner = MagicMock()
    cleaner.clean.return_value = "content"
    cleaner.chunk.return_value = []
    monkeypatch.setattr(
        "app.api.retrieval_engine.ingestion_service.SourceFactory.get_pdf_cleaner",
        lambda: (extractor, cleaner),
    )
    upload = MagicMock()
    upload.filename = "edited.pdf"

    with pytest.raises(ChunkingError):
        await ingestion_service.ingest_pdf_file(
            file=upload,
            source="pdf:new",
            domain="python",
            topic="rag",
            display_name="edited.pdf",
            replaces_source="pdf:old",
        )

    assert vector_store.delete_by_filter.call_count == 0


@pytest.mark.asyncio
async def test_url_ingestion_canonicalizes_source_and_forwards_replacement(
    ingestion_service: IngestionService, monkeypatch: pytest.MonkeyPatch
) -> None:
    extractor = MagicMock()
    extractor.extract = AsyncMock(return_value="<html>content</html>")
    cleaner = MagicMock()
    cleaner.clean.return_value = "content"
    cleaner.chunk.return_value = [ChunkWithMetadata(text="content")]
    monkeypatch.setattr(
        "app.api.retrieval_engine.ingestion_service.SourceFactory.get_extractor_and_cleaner",
        lambda _url: (extractor, cleaner),
    )
    captured: dict[str, object] = {}

    async def capture(**kwargs: object) -> dict[str, int]:
        """Capture the arguments passed to the ingestion pipeline."""
        captured.update(kwargs)
        return {"chunks_processed": 1, "new": 1, "updated": 0}

    monkeypatch.setattr(ingestion_service, "_process_ingestion", capture)

    await ingestion_service.ingest_document(
        url="https://example.com/docs?utm_source=x",
        source="HTTPS://Example.COM:443/docs?utm_source=x&b=2&a=1",
        domain="python",
        topic="rag",
        replaces_source="pdf:old",
    )

    assert (
        captured["source"],
        captured["display_name"],
        captured["replaces_source"],
    ) == ("https://example.com/docs?a=1&b=2", "https://example.com/docs?a=1&b=2", "pdf:old")


@pytest.mark.asyncio
async def test_pdf_ingestion_forwards_display_name_and_replacement(
    ingestion_service: IngestionService, monkeypatch: pytest.MonkeyPatch
) -> None:
    extractor = MagicMock()
    extractor.extract = AsyncMock(return_value="extracted text")
    cleaner = MagicMock()
    cleaner.clean.return_value = "content"
    cleaner.chunk.return_value = [ChunkWithMetadata(text="content")]
    monkeypatch.setattr(
        "app.api.retrieval_engine.ingestion_service.SourceFactory.get_pdf_cleaner",
        lambda: (extractor, cleaner),
    )
    captured: dict[str, object] = {}

    async def capture(**kwargs: object) -> dict[str, int]:
        """Capture the arguments passed to the ingestion pipeline."""
        captured.update(kwargs)
        return {"chunks_processed": 1, "new": 1, "updated": 0}

    monkeypatch.setattr(ingestion_service, "_process_ingestion", capture)
    upload = MagicMock()
    upload.filename = "edited.pdf"

    await ingestion_service.ingest_pdf_file(
        file=upload,
        source="pdf:new",
        domain="python",
        topic="rag",
        display_name="edited.pdf",
        replaces_source="pdf:old",
    )

    assert (captured["display_name"], captured["replaces_source"]) == (
        "edited.pdf",
        "pdf:old",
    )
