from pydantic import BaseModel, Field, ValidationInfo, field_validator

class IngestRequest(BaseModel):
    url: str
    domain: str = Field(default="general", min_length=1, max_length=50)
    topic: str = Field(default="unknown", min_length=1, max_length=50)
    replaces_source: str | None = None

    @field_validator("domain", "topic")
    @classmethod
    def normalize_lowercase(cls, v: str, info: ValidationInfo) -> str:
        """Normalize to lowercase and reject blank values."""
        normalized = v.lower().strip()
        if not normalized:
            raise ValueError(f"{info.field_name} must not be blank")
        return normalized

class SearchRequest(BaseModel):
    query: str = Field(min_length=5, max_length=1000)
    domain: str | None = Field(None, max_length=50)
    topic: str | None = Field(None, max_length=50)
    top_k: int = Field(ge=1, le=20)

    @field_validator("domain", "topic")
    @classmethod
    def normalize_lowercase(cls, v: str | None) -> str | None:
        """Normalize to lowercase"""
        if v:
            return v.lower().strip()
        return v
