from typing import Optional
from pydantic import BaseModel


class LLMConfig(BaseModel):
    api_key: str
    provider: str
    model: str = "mistral-small-latest"
    temperature: float = 0.0
    max_retries: int = 3
    url: Optional[str] = None
