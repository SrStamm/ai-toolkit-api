from .tools_registry import ToolResponse, register_tool
from ..prompt import PROMP_DIRECT, PROMP_DIRECT_WITH_CONTEXT
from ...rag.schemas import LLMAnswer

@register_tool(
    name="direct",
    description="Responde conocimiento general sin consultar documentos",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Pregunta del usuario"},
        },
        "required": ["question"],
    },
    dependencies=["llm_client"]
)
def direct_tool(query: str, context: str = "", llm_client=None):
    if context:
        prompt = PROMP_DIRECT_WITH_CONTEXT.format(context=context, question=query)
    else:
        prompt = PROMP_DIRECT.format(question=query)

    res = llm_client.generate_content(prompt)

    parsed = LLMAnswer.model_validate_json(res.content)

    return ToolResponse(
        output=parsed.answer
    )
