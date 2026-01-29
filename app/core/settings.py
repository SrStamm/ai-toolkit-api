from abc import ABC, abstractmethod
from .models import LLMResponse
from pydantic import BaseModel


class LLMConfig(BaseModel):
    api_key: str
    model: str = "mistral-small-latest"
    temperature: float = 0.0
    max_retries: int = 3


class BaseLLMProvider(ABC):
    @abstractmethod
    def chat(self, prompt: str) -> LLMResponse:
        pass
