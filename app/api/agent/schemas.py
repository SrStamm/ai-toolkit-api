from typing import List, Optional
from pydantic import BaseModel, Field
from enum import Enum


class ActionType(str, Enum):
    RETRIEVE_CONTEXT = "retrieve_context"
    CALL_TOOL = "call_tool"
    FINAL_ANSWER = "final_answer"


class AgentResponse(BaseModel):
    output: str
    session_id: str
    metadata: dict[str, object] = Field(default_factory=dict)


class QueryAgentRequest(BaseModel):
    text: str = Field(max_length=1000)
    session_id: str | None = Field(default=None)


class AgentState(BaseModel):
    query: str
    session_id: str
    top_k: int = 5
    history: Optional[List[str]] = None
    context: Optional[str] = None
    tool_results: List[str] = Field(default_factory=list)

    def add_tool_result(self, result: str) -> None:
        self.tool_results.append(result)


class Decision(BaseModel):
    action: ActionType
    tool_name: str | None = None
    args: dict = Field(default_factory=dict)
