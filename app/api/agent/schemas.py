from typing import Any, Optional
from pydantic import BaseModel, Field


class AgentResponse(BaseModel):
    output: str 
    session_id: str 
    metadata: dict[str, Any] = Field(default_factory=dict)

class QueryAgentRequest(BaseModel):
    text: str = Field(max_length=1000)
    session_id: Optional[str] = Field(default=None)

