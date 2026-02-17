# Provider for LLM

from abc import ABC, abstractmethod
from typing import Optional
from typing_extensions import AsyncIterator
from ..models import LLMResponse


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
