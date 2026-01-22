from pydantic import BaseModel, Field, HttpUrl


class IngestRequest(BaseModel):
    url: str
    domain: str = "general"
    topic: str = "unknown"


class QueryRequest(BaseModel):
    text: str = Field(min_length=5)
    domain: str = "general"
    topic: str = "unknown"
