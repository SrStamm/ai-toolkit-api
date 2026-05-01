"""
Document Management Tools for the Agent.

Provides tools to delete, inspect, and re-index documents in the vector store.
"""

from typing import Optional
from .tools_registry import ToolRegistry, ToolResponse
import structlog

logger = structlog.get_logger()


def _delete_document_handler(
    source: str,
    vector_store: Optional[object] = None,  # TYPE: Any para evitar import pesado
    **kwargs
) -> ToolResponse:
    """Handler para eliminar un documento (y sus chunks) de la base vectorial."""
    if vector_store is None:
        return ToolResponse(
            output="Error: Vector store not available",
            metadata={"error": "missing_dependency"},
        )

    try:
        vector_store.delete_by_filter({"source": source})
        msg = f"Document '{source}' deleted successfully."
        logger.info("tool_delete_document", source=source)
        return ToolResponse(
            output=msg,
            metadata={"source": source, "status": "deleted"},
        )
    except Exception as e:
        logger.error("tool_delete_document_error", source=source, error=str(e))
        return ToolResponse(
            output=f"Error deleting document: {str(e)}",
            metadata={"error": str(e)},
        )


def _get_document_metadata_handler(
    source: str,
    vector_store: Optional[object] = None,
    **kwargs
) -> ToolResponse:
    """Handler para obtener metadatos de un documento."""
    if vector_store is None:
        return ToolResponse(
            output="Error: Vector store not available",
            metadata={"error": "missing_dependency"},
        )

    try:
        metadata = vector_store.get_source_metadata(source)
        if metadata is None:
            return ToolResponse(
                output=f"Document '{source}' not found.",
                metadata={"source": source, "found": False},
            )

        # Format output for the agent
        output_str = (
            f"Source: {metadata['source']}\n"
            f"Domain: {metadata['domain']}\n"
            f"Topic: {metadata['topic']}\n"
            f"Chunks: {metadata['chunk_count']}\n"
            f"Last Ingested: {metadata['last_ingested']}"
        )
        return ToolResponse(output=output_str, metadata=metadata)
    except Exception as e:
        logger.error("tool_get_metadata_error", source=source, error=str(e))
        return ToolResponse(
            output=f"Error getting metadata: {str(e)}",
            metadata={"error": str(e)},
        )


def _list_documents_handler(
    domain: Optional[str] = None,
    vector_store: Optional[object] = None,
    **kwargs
) -> ToolResponse:
    """Handler para listar documentos disponibles."""
    if vector_store is None:
        return ToolResponse(
            output="Error: Vector store not available",
            metadata={"error": "missing_dependency"},
        )

    try:
        sources = vector_store.list_sources(domain=domain)
        if not sources:
            return ToolResponse(
                output="No documents found.",
                metadata={"count": 0},
            )

        output_lines = [f"Found {len(sources)} document(s):"]
        for src in sources:
            output_lines.append(
                f"- {src['source']} ({src['domain']}/{src['topic']}) - {src['chunk_count']} chunks"
            )

        return ToolResponse(
            output="\n".join(output_lines),
            metadata={"documents": sources, "count": len(sources)},
        )
    except Exception as e:
        logger.error("tool_list_documents_error", error=str(e))
        return ToolResponse(
            output=f"Error listing documents: {str(e)}",
            metadata={"error": str(e)},
        )


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
        import asyncio
        
        # 1. Delete old data (sync operation)
        logger.info("tool_reindex_start", source=source, url=url)
        ingestion_service.vector_store.delete_by_filter({"source": source})

        # 2. Ingest new data (async operation wrapped in sync)
        # Since the tool handler is sync but the service is async, we run the async code
        async def _do_ingest():
            return await ingestion_service.ingest_document(
                url=url, source=source, domain=domain, topic=topic
            )
        
        result = asyncio.run(_do_ingest())

        msg = f"Document '{source}' re-indexed successfully. Processed {result.get('chunks_processed',0)} chunks."
        logger.info("tool_reindex_success", source=source, **result)
        return ToolResponse(output=msg, metadata=result)

    except Exception as e:
        logger.error("tool_reindex_error", source=source, error=str(e))
        return ToolResponse(
            output=f"Error re-indexing document: {str(e)}",
            metadata={"error": str(e)},
        )

        msg = f"Document '{source}' re-indexed successfully. Processed {result.get('chunks_processed', 0)} chunks."
        logger.info("tool_reindex_success", source=source, **result)
        return ToolResponse(output=msg, metadata=result)

    except Exception as e:
        logger.error("tool_reindex_error", source=source, error=str(e))
        return ToolResponse(
            output=f"Error re-indexing document: {str(e)}",
            metadata={"error": str(e)},
        )


def register_document_tools() -> None:
    """Registra las tools de gestión de documentos en el registry."""
    
    # 1. Delete Document
    ToolRegistry.register(
        name="delete_document",
        description="Delete a document and all its chunks from the vector database using its source identifier. Use this when the user wants to remove specific documentation.",
        parameters={
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "description": "The source identifier of the document (usually the URL)",
                },
            },
            "required": ["source"],
        },
        handler=_delete_document_handler,
        dependencies=["vector_store"],
    )

    # 2. Get Document Metadata
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

    # 3. List Documents
    ToolRegistry.register(
        name="list_documents",
        description="List all documents available in the vector store. Optionally filter by domain.",
        parameters={
            "type": "object",
            "properties": {
                "domain": {
                    "type": "string",
                    "description": "Optional domain to filter results (e.g., 'python', 'docker')",
                },
            },
        },
        handler=_list_documents_handler,
        dependencies=["vector_store"],
    )

    # 4. Re-index Document
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
