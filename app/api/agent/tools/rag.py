"""
RAG Tool para el agente.

Busca en la base vectorial y construye respuesta con contexto.
"""

from .tools_registry import ToolRegistry, ToolResponse


def _rag_tool_handler(
    query: str, top_k: int = 5, rag_orchestrator=None, **kwargs
) -> ToolResponse:
    """Handler para la tool RAG."""
    if rag_orchestrator is None:
        return ToolResponse(
            output="Error: RAG orchestrator not available",
            metadata={"error": "missing_dependency"},
        )

    res = rag_orchestrator.get_context(query=query)
    return ToolResponse(
        output=res.answer,
        metadata={"citations": res.citations, "metadata": res.metadata},
    )


def register_rag_tool() -> None:
    """Registra la tool RAG en el registry."""
    ToolRegistry.register(
        name="rag",
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
            },
            "required": ["query"],
        },
        handler=_rag_tool_handler,
        dependencies=["rag_orchestrator"],
    )
