"""
RAG Tool para el agente.

Busca en la base vectorial y construye respuesta con contexto.
"""

from typing import Optional
from .tools_registry import ToolRegistry, ToolResponse
from ...llamaindex_adapter.orchestrator import LlamaIndexOrchestrator
import structlog

logger = structlog.get_logger()


def _retrieve_context_tool_handler(
    query: str,
    top_k: int = 5,
    domain: Optional[str] = None,
    rag_orchestrator: Optional[LlamaIndexOrchestrator] = None,
    **kwargs
) -> ToolResponse:
    """Handler para la tool RAG."""
    if rag_orchestrator is None:
        return ToolResponse(
            output="Error: RAG orchestrator not available",
            metadata={"error": "missing_dependency"},
        )

    logger.info("tool_variables", query=query, domain=domain)

    # get_context now returns (context_str, citations)
    context_str, citations = rag_orchestrator.get_context(
        query=query, top_k=top_k, domain=domain
    )

    # Convert citations to dicts for JSON serialization in metadata
    citations_dict = [citation.model_dump() for citation in citations]

    return ToolResponse(
        output=context_str,
        metadata={"citations": citations_dict},
    )


def register_retrieve_context_tool() -> None:
    """Registra la tool en el registry."""
    ToolRegistry.register(
        name="retrieve_context",
        description="Search in vector database. Use this when the user asks about information from documents or needs context from a knowledge base.",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "User query"},
                "top_k": {
                    "type": "integer",
                    "description": "Quantity of results",
                    "default": 5,
                },
                "domain": {
                    "type": "string",
                    "description": "Optional domain to filter results (e.g., 'libros', 'docs')",
                },
            },
            "required": ["query"],
        },
        handler=_retrieve_context_tool_handler,
        dependencies=["rag_orchestrator"],
    )
