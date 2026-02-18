from typing import Optional
from pydantic import BaseModel, Field, field_validator


class IngestRequest(BaseModel):
    url: str
    domain: str = Field(default="general", min_length=1, max_length=50)
    topic: str = Field(default="unknown", min_length=1, max_length=50)

    @field_validator("domain", "topic")
    @classmethod
    def normalize_lowercase(cls, v: str) -> str:
        """Normalize to lowercase"""
        return v.lower().strip()


class QueryRequest(BaseModel):
    text: str = Field(min_length=5, max_length=1000)
    domain: Optional[str] = Field(None, max_length=50)
    topic: Optional[str] = Field(None, max_length=50)

    @field_validator("domain", "topic")
    @classmethod
    def normalize_lowercase(cls, v: Optional[str]) -> Optional[str]:
        """Normalize to lowercase"""
        if v:
            return v.lower().strip()
        return v


class Citation(BaseModel):
    source: str
    chunk_index: int = Field(ge=0)


class Metadata(BaseModel):
    tokens: int = Field(ge=0)
    cost: float = Field(ge=0.0)
    model: Optional[str] = None
    provider: Optional[str] = None


class QueryResponse(BaseModel):
    answer: str
    citations: list[Citation]
    metadata: Metadata


class LLMAnswer(BaseModel):
    answer: str
