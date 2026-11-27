"""Unit tests for the query service's context and citation contract."""

import json
from collections.abc import AsyncIterator
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.api.retrieval_engine.exceptions import VectorStoreError
from app.api.retrieval_engine.query_service import QueryService
from app.api.retrieval_engine.schemas.query import Citation, QueryResponse


def _chunk(
    text: str, source: str, chunk_index: int | None = None
) -> SimpleNamespace:
    """Build a scored-point double with the payload shape used by Qdrant."""
    payload = {"text": text, "source": source}
    if chunk_index is not None:
        payload["chunk_index"] = chunk_index
    return SimpleNamespace(payload=payload)


def _llm_response() -> SimpleNamespace:
    """Build an LLM response double with explicit, valid usage values."""
    return SimpleNamespace(
        content='{"answer": "an answer"}',
        usage=SimpleNamespace(
            prompt_tokens=10, completion_tokens=5, total_tokens=15
        ),
        cost=SimpleNamespace(input_cost=0.001, output_cost=0.002, total_cost=0.003),
        model="test-model",
        provider="test",
    )


async def _stream_response(
    response: SimpleNamespace,
) -> AsyncIterator[tuple[str, SimpleNamespace | None]]:
    """Yield a content chunk followed by the final LLM response."""
    yield "an answer", None
    yield "", response


def _build_service(
    results: list[SimpleNamespace],
) -> tuple[QueryService, MagicMock, MagicMock, MagicMock, MagicMock]:
    """Create a query service with mock collaborators and fixed search results."""
    llm_client = MagicMock()
    vector_store = MagicMock()
    embed_service = MagicMock()
    reranker = MagicMock()
    metrics = MagicMock()
    vector_store.query.return_value = results
    reranker.rerank.return_value = results
    service = QueryService(
        llm_client, vector_store, embed_service, reranker, metrics
    )
    return service, vector_store, embed_service, reranker, metrics


def test_get_context_builds_numbered_context() -> None:
    chunks = [_chunk("first", "a.pdf"), _chunk("second", "b.pdf")]
    service, _, _, _, _ = _build_service(chunks)

    context, _ = service.get_context("question")

    assert context == "[1]\nfirst\n\n[2]\nsecond"


def test_get_context_deduplicates_citations_in_first_seen_order() -> None:
    chunks = [
        _chunk("one", "a.pdf"),
        _chunk("two", "b.pdf"),
        _chunk("three", "a.pdf"),
        _chunk("four", "c.pdf"),
    ]
    service, _, _, _, _ = _build_service(chunks)

    _, citations = service.get_context("question")

    assert citations == ["a.pdf", "b.pdf", "c.pdf"]


def test_get_context_returns_empty_result_when_store_is_empty() -> None:
    service, _, _, _, _ = _build_service([])

    assert service.get_context("question") == ("", [])


def test_get_context_skips_reranking_when_store_is_empty() -> None:
    service, _, _, reranker, _ = _build_service([])

    service.get_context("question")

    reranker.rerank.assert_not_called()


def test_retrieve_embeds_the_query_in_query_mode() -> None:
    service, _, embed_service, _, _ = _build_service([])

    service.get_context("question")

    embed_service.embed.assert_called_once_with("question", query=True)


def test_retrieve_queries_the_store_with_limit_20() -> None:
    service, vector_store, _, _, _ = _build_service([])

    service.get_context("question")

    assert vector_store.query.call_args.kwargs["limit"] == 20


def test_retrieve_lowercases_domain_and_topic_filters() -> None:
    service, vector_store, _, _, _ = _build_service([])

    service.get_context("question", domain="Python", topic="RAG")

    filter_context = vector_store.query.call_args.kwargs["filter_context"]
    assert (filter_context.domain, filter_context.topic) == ("python", "rag")


def test_retrieve_logs_vector_search_metrics() -> None:
    chunks = [_chunk("one", "a.pdf"), _chunk("two", "b.pdf")]
    service, _, _, _, metrics = _build_service(chunks)

    service.get_context("question")

    assert metrics.log_vector_search.call_args.kwargs["chunks_found"] == 2


def test_get_context_truncates_results_to_top_k() -> None:
    chunks = [_chunk("one", "a.pdf"), _chunk("two", "b.pdf"), _chunk("three", "c.pdf")]
    service, _, _, _, _ = _build_service(chunks)

    context, citations = service.get_context("question", top_k=2)

    assert (context, citations) == (
        "[1]\none\n\n[2]\ntwo",
        ["a.pdf", "b.pdf"],
    )


def test_get_context_propagates_store_errors() -> None:
    service, vector_store, _, _, _ = _build_service([])
    vector_store.query.side_effect = VectorStoreError("store unavailable")

    with pytest.raises(VectorStoreError, match="store unavailable"):
        service.get_context("question")


def test_ask_returns_query_response() -> None:
    service, _, _, _, _ = _build_service([_chunk("first", "a.pdf")])
    service.llm_client.generate_content.return_value = _llm_response()

    response = service.ask(uuid4(), "question")

    assert isinstance(response, QueryResponse)


def test_ask_builds_citation_objects_from_chunk_payloads() -> None:
    chunks = [
        _chunk("first", "a.pdf", chunk_index=2),
        _chunk("second", "a.pdf"),
    ]
    service, _, _, _, _ = _build_service(chunks)
    service.llm_client.generate_content.return_value = _llm_response()

    response = service.ask(uuid4(), "question")

    assert response.citations == [
        Citation(source="a.pdf", chunk_index=2, text="first"),
        Citation(source="a.pdf", chunk_index=0, text="second"),
    ]


@pytest.mark.asyncio
async def test_chat_stream_emits_serialized_citation_objects() -> None:
    chunks = [
        _chunk("first", "a.pdf", chunk_index=4),
        _chunk("second", "b.pdf", chunk_index=7),
    ]
    service, _, _, _, _ = _build_service(chunks)
    service.llm_client.generate_content_stream.return_value = _stream_response(
        _llm_response()
    )

    events = [
        json.loads(line.removeprefix("data: "))
        async for line in service.chat_stream(uuid4(), "question")
    ]

    assert [event for event in events if event["type"] == "citations"][0][
        "citations"
    ] == [
        {"source": "a.pdf", "chunk_index": 4, "text": "first"},
        {"source": "b.pdf", "chunk_index": 7, "text": "second"},
    ]
