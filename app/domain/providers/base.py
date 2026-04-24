"""
Base provider interface for LLM providers.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import TypedDict
from ...domain.models import LLMResponse


class Message(TypedDict):
    """Chat message with role and content."""
    role: str
    content: str


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    name: str
    model: str

    @abstractmethod
    def chat(self, prompt: str) -> LLMResponse:
        """Synchronous chat completion."""
        ...

    @abstractmethod
    def chat_with_messages(
        self,
        messages: list[Message],
        system_prompt: str | None = None,
    ) -> LLMResponse:
        """
        Synchronous chat with message history.

        Args:
            messages: List of messages with role and content.
            system_prompt: Optional system prompt to prepend.
        """
        ...

    @abstractmethod
    async def chat_stream(
        self, prompt: str
    ) -> AsyncIterator[tuple[str, LLMResponse | None]]:
        """Streaming chat completion."""
        ...
