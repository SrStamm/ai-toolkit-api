from api.rag.schemas import LLMAnswer
from .tools_registry import ToolResponse, register_tool
from ..prompt import PROMP_DIRECT

@register_tool(
    name="direct",
    description="Responde conocimiento general sin consultar documentos",
    parameters={
        "type": "object",
        "properties": {
            "question": {"type": "string", "description": "Pregunta del usuario"},
        },
        "required": ["question"]
    }
)
def direct_tool(query: str, llm_client=None):
    prompt = PROMP_DIRECT.format(question=query)
    res = llm_client.generate_content(prompt)

    parsed = LLMAnswer.model_validate_json(res.content)

    return ToolResponse(
        output=parsed.answer
    )
