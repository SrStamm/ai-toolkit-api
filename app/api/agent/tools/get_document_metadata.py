"""
Get Document Metadata Tool.

Obtiene metadatos de un documento específico en el vector store.
"""

import time
from typing import Optional
import structlog

from .tools_registry import ToolExecutionResult, ToolRegistry, ToolStatus
from ....infrastructure.storage.interfaces import VectorStoreInterface

logger = structlog.get_logger()


def _get_document_metadata_handler(
    source: str,
    vector_store: Optional[VectorStoreInterface] = None,
    **kwargs
) -> ToolExecutionResult:
    start = time.perf_counter()

    """Handler para obtener metadatos de un documento."""
    if vector_store is None:
        return ToolExecutionResult(
            tool_name="get_document_metadata",
            output="Error: Vector store not available",
            metadata={"error": "missing_dependency"},
            status=ToolStatus.FAILED,
            execution_time_ms=int(time.perf_counter() - start)
        )

    try:
        metadata = vector_store.get_source_metadata(source)
        if metadata is None:
            return ToolExecutionResult(
            tool_name="get_document_metadata",
                output=f"Document '{source}' not found.",
                metadata={"source": source, "found": False},
                status=ToolStatus.FAILED,
                execution_time_ms=int(time.perf_counter() - start)
            )

        output_str = (
            f"Source: {metadata['source']}\n"
            f"Domain: {metadata['domain']}\n"
            f"Topic: {metadata['topic']}\n"
            f"Chunks: {metadata['chunk_count']}\n"
            f"Last Ingested: {metadata['last_ingested']}"
        )
        return ToolExecutionResult(
            tool_name="get_document_metadata",
            output=output_str, metadata=metadata,
            status=ToolStatus.SUCCESS,
            execution_time_ms=int(time.perf_counter() - start)
            )
    except Exception as e:
        logger.error("tool_get_metadata_error", source=source, error=str(e))
        return ToolExecutionResult(
            tool_name="get_document_metadata",
            output=f"Error getting metadata: {str(e)}",
            metadata={"error": str(e)},
            status=ToolStatus.FAILED,
            execution_time_ms=int(time.perf_counter() - start)
        )


def register_get_document_metadata_tool() -> None:
    """Registra la tool en el registry."""
    ToolRegistry.register(
        name="get_document_metadata",
        description="Get metadata about a specific document in the vector store (domain, topic, chunk count). Use this to inspect a document before deleting or re-indexing.",
        parameters={
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "description": "The source identifier of the document",
                },
            },
            "required": ["source"],
        },
        handler=_get_document_metadata_handler,
        dependencies=["vector_store"],
    )
