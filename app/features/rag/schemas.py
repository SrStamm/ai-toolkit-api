from pydantic import BaseModel, Field


class IngestRequest(BaseModel):
    url: str
    domain: str = "general"
    topic: str = "unknown"


class QueryRequest(BaseModel):
    text: str = Field(min_length=5)
    domain: str | None = None
    topic: str | None = None


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
