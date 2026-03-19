from abc import ABC, abstractmethod
from typing import Any
from pydantic import BaseModel, Field

from .prompt import PROMP_DIRECT
from ..rag.schemas import LLMAnswer
from ..llamaindex.orchrestator import (
    LlamaIndexOrchestrator,
    LLMClient,
)

class ToolResponse(BaseModel):
    output: str
    metadata: dict[str, Any] = Field(default_factory=dict)

class Tool(ABC):
    name: str
    description: str

    @abstractmethod
    def execute(self, input: str) -> ToolResponse:
        pass

class RagTool(Tool):
    name = "rag"
    description = "Busqueda en base vectorial"

    def __init__(self, rag: LlamaIndexOrchestrator):
        self.rag = rag

    def execute(self, input: str) -> ToolResponse:
        res = self.rag.custom_query(query=input)
        return ToolResponse(
            output=res.answer,
            metadata={
                "citations": res.citations,
                "metadata": res.metadata
            }
        )

class DirectTool(Tool):
    name = "direct"

    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    def execute(self, input: str) -> ToolResponse:
        prompt = PROMP_DIRECT.format(question=input)
        res = self.llm.generate_content(prompt)

        parsed = LLMAnswer.model_validate_json(res.content)

        return ToolResponse(
            output=parsed.answer
        )

