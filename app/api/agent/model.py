from abc import ABC, abstractmethod
from typing import Any
from pydantic import BaseModel
from ..llamaindex.orchrestator import (
    LlamaIndexOrchestrator,
    get_orchestrator,
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

def build_tool_registry():
    return {
        "rag": rag_instance(),
    }
