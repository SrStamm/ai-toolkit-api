from abc import ABC, abstractmethod
from typing import Any
from pydantic import BaseModel

from .prompt import PROMP_DIRECT
from ..llamaindex.orchrestator import (
    LlamaIndexOrchestrator,
    LLMClient,
    get_orchestrator,
    get_llm_client
)

class ToolResponse(BaseModel):
    output: str
    metadata: dict[str, Any] = {}

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

def rag_instance() -> RagTool:
    rag=get_orchestrator()
    return RagTool(rag)

class DirectTool(Tool):
    name = "direct"

    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    def execute(self, input: str) -> ToolResponse:
        prompt = PROMP_DIRECT.format(question=input)
        res = self.llm.generate_content(prompt)

        return ToolResponse(
            output=res.content
        )


def direct_instance() -> DirectTool:
    llm=get_llm_client()
    return DirectTool(llm)

def build_tool_registry():
    return {
        "rag": rag_instance(),
        "direct": direct_instance()
    }
