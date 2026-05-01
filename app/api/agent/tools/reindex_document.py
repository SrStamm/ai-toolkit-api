"""
Reindex Document Tool.

Elimina la versión anterior de un documento e ingesta la nueva.
"""

import asyncio
from typing import Optional
from .tools_registry import ToolRegistry, ToolResponse
import structlog

logger = structlog.get_logger()


def _reindex_document_handler(
    source: str,
    url: str,
    domain: str,
    topic: str,
    ingestion_service: Optional[object] = None,
    **kwargs
) -> ToolResponse:
    """
    Handler para re-indexar un documento.
    Elimina la versión anterior e ingesta la nueva desde la URL.
    """
    if ingestion_service is None:
        return ToolResponse(
            output="Error: Ingestion service not available",
            metadata={"error": "missing_dependency"},
        )

    try:
        # 1. Delete old data (sync operation)
        logger.info("tool_reindex_start", source=source, url=url)
        ingestion_service.vector_store.delete_by_filter({"source": source})

        # 2. Ingest new data (async operation wrapped in sync)
        async def _do_ingest():
            return await ingestion_service.ingest_document(
                url=url, source=source, domain=domain, topic=topic
            )
        
        # Use asyncio.run to execute the async ingest within this sync handler
        result = asyncio.run(_do_ingest())

        msg = f"Document '{source}' re-indexed successfully. Processed {result.get('chunks_processed', 0)} chunks."
        logger.info("tool_reindex_success", source=source, processed=result.get('chunks_processed', 0))
        return ToolResponse(output=msg, metadata=result)

    except Exception as e:
        logger.error("tool_reindex_error", source=source, error=str(e))
        return ToolResponse(
            output=f"Error re-indexing document: {str(e)}",
            metadata={"error": str(e)},
        )


def register_reindex_document_tool() -> None:
    """Registra la tool en el registry."""
    ToolRegistry.register(
        name="reindex_document",
        description="Re-index a document from a URL. Deletes the old version and ingests the new one. Requires URL, source, domain, and topic.",
        parameters={
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "description": "The source identifier for the document",
                },
                "url": {
                    "type": "string",
                    "description": "The URL to fetch the new content from",
                },
                "domain": {
                    "type": "string",
                    "description": "The domain category (e.g., 'python', 'fastapi')",
                },
                "topic": {
                    "type": "string",
                    "description": "The topic category (e.g., 'routing', 'auth')",
                },
            },
            "required": ["source", "url", "domain", "topic"],
        },
        handler=_reindex_document_handler,
        dependencies=["ingestion_service"],
    )
