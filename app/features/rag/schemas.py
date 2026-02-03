from typing import Optional
from pydantic import BaseModel, Field


class IngestRequest(BaseModel):
    url: str
    domain: str = "general"
    topic: str = "unknown"


class QueryRequest(BaseModel):
    text: str = Field(min_length=5)
    domain: Optional[str] = None
    topic: Optional[str] = None


class Citation(BaseModel):
    source: str
    chunk_index: int


class Metadata(BaseModel):
    tokens: int
    cost: float


class QueryResponse(BaseModel):
    answer: str
    citations: list[Citation]
    metadata: Metadata


class LLMAnswer(BaseModel):
    answer: str
