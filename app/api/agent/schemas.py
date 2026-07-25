from typing import List, Optional
from pydantic import BaseModel, Field
from enum import Enum

from .tools.tools_registry import ToolExecutionResult
from .session_memory import Message


class ActionType(str, Enum):
    CALL_TOOL = "call_tool"
    ASK_USER = "ask_user"
    FINAL_ANSWER = "final_answer"


class AgentResponse(BaseModel):
    output: str
    session_id: str
    metadata: dict[str, object] = Field(default_factory=dict)


class QueryAgentRequest(BaseModel):
    text: str = Field(max_length=1000)
    session_id: str | None = Field(default=None)
    file_uuid: str | None = Field(default=None)
    filename: str | None = Field(default=None)


class AgentState(BaseModel):
    query: str
    session_id: str
    top_k: int = 5
    domain: Optional[str] = None  # Dominio opcional para filtrar búsquedas
    history: Optional[List[Message]] = None
    context: Optional[str] = None
    tool_results: List[str] = Field(default_factory=list)
    citations: List[dict] = Field(default_factory=list)  # Citaciones acumuladas
    complete: bool = False
    
    # Archivos adjuntos (PDF)
    file_uuid: str | None = None
    filename: str | None = None
    
    # Trazabilidad de herramientas
    last_tool: str | None = None
    last_tool_result: str | None = None
    last_tool_metadata: dict | None = None  # Metadatos crudos de la tool (ej: task_id)
    tool_execution_count: int = 0

    def add_tool_result(self, result: str) -> None:
        self.tool_results.append(result)
    
    def set_last_tool(self, tool_name: str, result: str, metadata: dict | None = None) -> None:
        """Registra la última tool ejecutada y sus metadatos."""
        self.last_tool = tool_name
        self.last_tool_result = result
        self.last_tool_metadata = metadata  # Guardar metadatos crudos
        self.tool_execution_count += 1
        self.add_tool_result(result)
        
        # Si hay citaciones en el metadata, acumularlas
        if metadata and "citations" in metadata:
            self.citations.extend(metadata["citations"])

    def apply(self, response: ToolExecutionResult):
        self.context = response.output

        self.last_tool = response.tool_name
        self.last_tool_result = response.output
        self.last_tool_metadata = response.metadata
        self.tool_execution_count += 1
        self.add_tool_result(response.output)

        # Si hay citaciones en el metadata, acumularlas
        if response.metadata and "citations" in response.metadata:
            self.citations.extend(response.metadata["citations"])


class Decision(BaseModel):
    action: ActionType
    tool_name: str | None = None
    args: dict = Field(default_factory=dict)


class EventType(str, Enum):
    LLM_TOKEN = "llm_token" 
    DONE = 'done'


class AgentEvent(BaseModel):
    type: EventType
    content: str | None = None
    token: str | None = None
    metadata: dict = Field(default_factory=dict)
