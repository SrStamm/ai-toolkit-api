from .tools_registry import ToolResponse, register_tool

@register_tool(
    name="rag",
    description="Search in vector database",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "User query"},
            "top_k": {"type": "integer", "description": "Quantity of results", "default": 5}
        },
        "required": ["query"]
    },
    dependencies=["rag_orchestrator"]
)
def rag_tool(query: str, top_k: int = 5, rag_orchestrator=None, **kweargs):
    res = rag_orchestrator.custom_query(query=query)
    return ToolResponse(
        output=res.answer,
        metadata={
            "citations": res.citations,
            "metadata": res.metadata
        }
    )
