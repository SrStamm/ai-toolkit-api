"""
List Documents Tool.

Lista todos los documentos disponibles en el vector store.
"""

from typing import Optional
import structlog

from .tools_registry import ToolRegistry, ToolResponse
from ....infrastructure.storage.interfaces import VectorStoreInterface

logger = structlog.get_logger()


def _list_documents_handler(
    domain: Optional[str] = None,
    vector_store: Optional[VectorStoreInterface] = None,
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


def register_list_documents_tool() -> None:
    """Registra la tool en el registry."""
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
