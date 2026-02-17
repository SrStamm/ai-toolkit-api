from abc import ABC, abstractmethod
from typing import Optional
from typing_extensions import AsyncIterator
from ..domain.models import LLMResponse
from pydantic import BaseModel


class LLMConfig(BaseModel):
    api_key: str
    model: str = "mistral-small-latest"
    temperature: float = 0.0
    max_retries: int = 3
    url: Optional[str] = None


class BaseLLMProvider(ABC):
    name: str
    model: str

    @abstractmethod
    def chat(self, prompt: str) -> LLMResponse:
        pass

    @abstractmethod
    async def chat_stream(
        self, prompt: str
    ) -> AsyncIterator[tuple[str, Optional[LLMResponse]]]:
        pass
