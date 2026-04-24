from typing import List, Optional
from pydantic import BaseModel, Field


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
