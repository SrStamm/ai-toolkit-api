from pydantic import BaseModel, Field, field_validator

class QueryRequest(BaseModel):
    text: str = Field(min_length=5, max_length=1000)
    domain: str | None = Field(None, max_length=50)
    topic: str | None = Field(None, max_length=50)

    @field_validator("domain", "topic")
    @classmethod
    def normalize_lowercase(cls, v: str | None) -> str | None:
        """Normalize to lowercase"""
        if v:
            return v.lower().strip()
        return v

class Citation(BaseModel):
    source: str
    chunk_index: int = Field(ge=0)
    text: str

class Metadata(BaseModel):
    tokens: int = Field(ge=0)
    cost: float = Field(ge=0.0)
    model: str | None = None
    provider: str | None = None

class QueryResponse(BaseModel):
    answer: str
    citations: list[Citation]
    metadata: Metadata

class LLMAnswer(BaseModel):
    answer: str
