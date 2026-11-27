"""Guard tests for the RAG-only OpenAPI generation path."""

import importlib
from unittest.mock import patch

from fastapi import FastAPI

generate_openapi = importlib.import_module("scripts.generate-openapi")
build_schema_app = generate_openapi.build_schema_app

EXPECTED_PATHS = {
    "/rag/search",
    "/rag/documents",
    "/rag/documents/{source}",
    "/rag/documents/metadata",
    "/rag/ingest/job",
    "/rag/ingest-file/job",
    "/rag/job/{job_id}",
}

EXPECTED_OPERATION_IDS = {
    "searchDocuments",
    "listDocuments",
    "deleteDocument",
    "getDocumentMetadata",
    "ingestDocumentJob",
    "ingestFileJob",
    "getJobStatus",
}


def test_generated_app_has_no_lifespan_events() -> None:
    app: FastAPI = build_schema_app()

    assert (app.router.on_startup, app.router.on_shutdown) == ([], [])


def test_openapi_contains_only_the_seven_rag_paths() -> None:
    schema = build_schema_app().openapi()

    assert set(schema["paths"]) == EXPECTED_PATHS


def test_operation_ids_are_frozen() -> None:
    schema = build_schema_app().openapi()
    operation_ids = {
        operation["operationId"]
        for path in schema["paths"].values()
        for operation in path.values()
    }

    assert operation_ids == EXPECTED_OPERATION_IDS


def test_schema_generation_does_not_initialize_qdrant() -> None:
    with (
        patch(
            "app.infrastructure.storage.qdrant_client.get_qdrant_store",
            side_effect=AssertionError("Qdrant must not be initialized"),
        ) as get_store,
        patch(
            "app.infrastructure.storage.qdrant_client.QdrantStore.create_collection",
            side_effect=AssertionError("Qdrant collection must not be created"),
        ) as create_collection,
    ):
        build_schema_app().openapi()

    assert (get_store.called, create_collection.called) == (False, False)
