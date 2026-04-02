"""
Base provider interface for LLM providers.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from app.domain.models import LLMResponse


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    name: str
    model: str

    @abstractmethod
    def chat(self, prompt: str) -> LLMResponse:
        """Synchronous chat completion."""
        ...

    @abstractmethod
    async def chat_stream(
        self, prompt: str
    ) -> AsyncIterator[tuple[str, LLMResponse | None]]:
        """Streaming chat completion."""
        ...
