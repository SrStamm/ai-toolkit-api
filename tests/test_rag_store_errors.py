"""Unit tests for QdrantStore error translation and filter construction."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.api.retrieval_engine.exceptions import InvalidFilterError, VectorStoreError
from app.api.retrieval_engine.schemas.response import SourceMetadata
from app.infrastructure.storage.interfaces import FilterContext, HybridVector
from app.infrastructure.storage.qdrant_client import QdrantStore


@pytest.fixture(autouse=True)
def no_rerank_model(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prevent the store constructor from loading a real reranker model."""
    monkeypatch.setattr(
        "app.infrastructure.storage.qdrant_client.get_rerank_model",
        lambda: MagicMock(),
    )


@pytest.fixture
def client() -> MagicMock:
    """Return a mock Qdrant client with no network access."""
    return MagicMock()


@pytest.fixture
def store(client: MagicMock) -> QdrantStore:
    """Return a store backed by the mock client."""
    return QdrantStore(client=client)


def test_delete_by_filter_rejects_empty_conditions(store: QdrantStore) -> None:
    with pytest.raises(
        InvalidFilterError, match="delete_by_filter requires at least one condition"
    ):
        store.delete_by_filter({})


def test_delete_by_filter_translates_client_error(
    store: QdrantStore, client: MagicMock
) -> None:
    client.delete.side_effect = RuntimeError("boom")

    with pytest.raises(
        VectorStoreError, match="Failed to delete points by filter"
    ):
        store.delete_by_filter({"source": "a.pdf"})


def test_delete_by_filter_builds_lt_range(
    store: QdrantStore, client: MagicMock
) -> None:
    store.delete_by_filter({"ingested_at_lt": 100})

    condition = client.delete.call_args.kwargs["points_selector"].filter.must[0]
    assert condition.range.lt == 100


def test_delete_by_filter_builds_gt_range(
    store: QdrantStore, client: MagicMock
) -> None:
    store.delete_by_filter({"ingested_at_gt": 50})

    condition = client.delete.call_args.kwargs["points_selector"].filter.must[0]
    assert condition.range.gt == 50


def test_query_without_filters_passes_no_filter(
    store: QdrantStore, client: MagicMock
) -> None:
    query_vector = HybridVector(
        dense=[0.1, 0.2], sparse={"indices": [1, 2], "values": [0.3, 0.4]}
    )

    store.query(query_vector, limit=5, filter_context=FilterContext())

    assert client.query_points.call_args.kwargs["query_filter"] is None


def test_create_collection_translates_client_error(
    store: QdrantStore, client: MagicMock
) -> None:
    client.collection_exists.return_value = False
    client.create_collection.side_effect = RuntimeError("boom")

    with pytest.raises(VectorStoreError, match="Failed to create collection"):
        store.create_collection()


def test_list_sources_tracks_max_last_ingested(
    store: QdrantStore, client: MagicMock
) -> None:
    client.scroll.return_value = (
        [
            SimpleNamespace(
                payload={
                    "source": "a.pdf",
                    "domain": "python",
                    "topic": "rag",
                    "ingested_at": 100,
                }
            ),
            SimpleNamespace(
                payload={
                    "source": "a.pdf",
                    "domain": "python",
                    "topic": "rag",
                    "ingested_at": 300,
                }
            ),
            SimpleNamespace(
                payload={"source": "a.pdf", "domain": "python", "topic": "rag"}
            ),
        ],
        None,
    )

    rows = store.list_sources()

    assert rows[0]["last_ingested"] == 300


def test_list_sources_row_validates_as_source_metadata(
    store: QdrantStore, client: MagicMock
) -> None:
    client.scroll.return_value = (
        [
            SimpleNamespace(
                payload={"source": "a.pdf", "domain": "python", "topic": "rag"}
            )
        ],
        None,
    )

    metadata = SourceMetadata(**store.list_sources()[0])

    assert metadata.last_ingested == 0


def test_list_sources_merges_alias_rows(
    store: QdrantStore, client: MagicMock
) -> None:
    client.scroll.return_value = (
        [
            SimpleNamespace(
                payload={
                    "source": "https://example.com/docs",
                    "domain": "python",
                    "topic": "rag",
                    "ingested_at": 100,
                }
            ),
            SimpleNamespace(
                payload={
                    "source": "HTTPS://Example.COM:443/docs",
                    "domain": "python",
                    "topic": "rag",
                    "ingested_at": 300,
                }
            ),
        ],
        None,
    )

    assert store.list_sources() == [
        {
            "source": "https://example.com/docs",
            "display_name": "https://example.com/docs",
            "domain": "python",
            "topic": "rag",
            "chunk_count": 2,
            "last_ingested": 300,
        }
    ]


def test_list_sources_carries_display_name_from_alias(
    store: QdrantStore, client: MagicMock
) -> None:
    client.scroll.return_value = (
        [
            SimpleNamespace(
                payload={"source": "https://example.com/docs", "domain": "python"}
            ),
            SimpleNamespace(
                payload={
                    "source": "HTTPS://Example.COM:443/docs",
                    "display_name": "Docs",
                    "domain": "python",
                }
            ),
        ],
        None,
    )

    assert store.list_sources()[0]["display_name"] == "Docs"


def test_get_source_metadata_merges_legacy_alias(
    store: QdrantStore, client: MagicMock
) -> None:
    client.scroll.side_effect = [
        (
            [
                SimpleNamespace(
                    payload={
                        "source": "https://example.com/docs",
                        "display_name": "Docs",
                        "domain": "python",
                        "topic": "rag",
                        "ingested_at": 100,
                    }
                )
            ],
            None,
        ),
        (
            [
                SimpleNamespace(
                    payload={
                        "source": "HTTPS://Example.COM:443/docs",
                        "domain": "python",
                        "topic": "rag",
                        "ingested_at": 300,
                    }
                )
            ],
            None,
        ),
    ]

    assert store.get_source_metadata("HTTPS://Example.COM:443/docs") == {
        "source": "https://example.com/docs",
        "display_name": "Docs",
        "domain": "python",
        "topic": "rag",
        "chunk_count": 2,
        "last_ingested": 300,
    }


def test_get_source_metadata_paginates_scroll(
    store: QdrantStore, client: MagicMock
) -> None:
    client.scroll.side_effect = [
        (
            [
                SimpleNamespace(
                    payload={
                        "source": "https://example.com/docs",
                        "domain": "python",
                        "ingested_at": 100,
                    }
                )
            ],
            "next-page",
        ),
        (
            [
                SimpleNamespace(
                    payload={
                        "source": "https://example.com/docs",
                        "domain": "python",
                        "ingested_at": 300,
                    }
                )
            ],
            None,
        ),
    ]

    metadata = store.get_source_metadata("https://example.com/docs")

    assert metadata is not None and metadata["chunk_count"] == 2


def test_get_source_metadata_scrolls_in_batches_of_256(
    store: QdrantStore, client: MagicMock
) -> None:
    client.scroll.return_value = ([], None)

    store.get_source_metadata("https://example.com/docs")

    assert client.scroll.call_args.kwargs["limit"] == 256
