"""
Direct Tool para el agente.

Responde conocimiento general sin consultar documentos.
"""

from app.api.agent.tools.tools_registry import ToolRegistry, ToolResponse
from app.api.agent.prompt import PROMP_DIRECT, PROMP_DIRECT_WITH_CONTEXT


def _direct_tool_handler(
    query: str, context: str = "", llm_client=None, **kwargs
) -> ToolResponse:
    """Handler para la tool direct."""
    if llm_client is None:
        return ToolResponse(
            output="Error: LLM client not available",
            metadata={"error": "missing_dependency"},
        )

    if context:
        prompt = PROMP_DIRECT_WITH_CONTEXT.format(context=context, question=query)
    else:
        prompt = PROMP_DIRECT.format(question=query)

    res = llm_client.generate_content(prompt)

    # Intentar parsear la respuesta como JSON
    try:
        from app.api.retrieval_engine.schemas import LLMAnswer

        parsed = LLMAnswer.model_validate_json(res.content)
        output = parsed.answer
    except Exception:
        output = res.content

    return ToolResponse(output=output)


def register_direct_tool() -> None:
    """Registra la tool direct en el registry."""
    ToolRegistry.register(
        name="direct",
        description="Responds to general knowledge questions without consulting documents. Use for greetings, casual conversation, or questions that don't require specific document context.",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "User question"},
            },
            "required": ["query"],
        },
        handler=_direct_tool_handler,
        dependencies=["llm_client"],
    )
