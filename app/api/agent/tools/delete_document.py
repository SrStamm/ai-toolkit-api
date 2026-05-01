"""
Delete Document Tool.

Elimina un documento y todos sus chunks de la base vectorial.
"""

from typing import Optional
import structlog

from .tools_registry import ToolRegistry, ToolResponse
from ....infrastructure.storage.interfaces import VectorStoreInterface

logger = structlog.get_logger()


def _delete_document_handler(
    source: str,
    vector_store: Optional[VectorStoreInterface] = None,
    **kwargs
) -> ToolResponse:
    """Handler para eliminar un documento de la base vectorial."""
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


def register_delete_document_tool() -> None:
    """Registra la tool en el registry."""
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
