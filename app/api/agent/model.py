from abc import ABC, abstractmethod
from ..llamaindex.orchrestator import (
    LlamaIndexOrchestrator,
    get_orchestrator,
)

class Tool(ABC):
    name: str
    description: str

    @abstractmethod
    def execute(self, input: str):
        pass

TOOLS = {}

class RagTool(Tool):
    name = "rag"
    description = "Busqueda en base vectorial"

    def __init__(self, rag: LlamaIndexOrchestrator):
        self.rag = rag

    def execute(self, input: str):
        return self.rag.custom_query(query=input)

def rag_instance() -> RagTool:
    rag=get_orchestrator()
    return RagTool(rag)
