"""
Delete Document Tool.

Elimina un documento y todos sus chunks de la base vectorial.
"""

import time
from typing import Optional
import structlog

from .tools_registry import ToolRegistry, ToolExecutionResult, ToolStatus
from ....infrastructure.storage.interfaces import VectorStoreInterface

logger = structlog.get_logger()


def _delete_document_handler(
    source: str,
    vector_store: Optional[VectorStoreInterface] = None,
    **kwargs
) -> ToolExecutionResult:
    start = time.perf_counter()

    """Handler para eliminar un documento de la base vectorial."""
    if vector_store is None:
        return ToolExecutionResult(
            tool_name="delete_document",
            output="Error: Vector store not available",
            metadata={"error": "missing_dependency"},
            status=ToolStatus.FAILED,
            execution_time_ms=int(time.perf_counter() - start)
        )

    try:
        vector_store.delete_by_filter({"source": source})
        msg = f"Document '{source}' deleted successfully."
        logger.info("tool_delete_document", source=source)
        return ToolExecutionResult(
            tool_name="delete_document",
            output=msg,
            metadata={"source": source, "status": "deleted"},
            status=ToolStatus.SUCCESS,
            execution_time_ms=int(time.perf_counter() - start)
        )
    except Exception as e:
        logger.error("tool_delete_document_error", source=source, error=str(e))
        return ToolExecutionResult(
            tool_name="delete_document",
            output=f"Error deleting document: {str(e)}",
            metadata={"error": str(e)},
            status=ToolStatus.FAILED,
            execution_time_ms=int(time.perf_counter() - start)
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
