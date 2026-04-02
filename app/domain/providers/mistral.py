"""
Mistral AI provider implementation.
"""

from collections.abc import AsyncIterator
from typing import Callable

from mistralai.client import Mistral
from httpx import ConnectError, NetworkError, TimeoutException

from app.core.settings import LLMConfig
from app.domain.models import LLMResponse, TokenUsage
from app.domain.services.pricing import ModelPricing
from app.domain.providers.retryable_provider import RetryableProvider


class MistralProvider(RetryableProvider):
    """
    Mistral AI provider using the RetryableProvider base.
    """

    def _setup_provider(self) -> None:
        """Setup Mistral-specific attributes."""
        self.client = Mistral(api_key=self.config.api_key)
        self.name = "mistral"
        self.model = self.config.model

    def _get_retryable_exceptions(self) -> tuple[type[Exception], ...]:
        """Mistral-specific retryable exceptions."""
        return (
            TimeoutError,
            ConnectionError,
            ConnectError,
            TimeoutException,
            NetworkError,
        )

    def _execute_chat_sync(self, prompt: str) -> LLMResponse:
        """Execute synchronous chat with Mistral."""
        chat_response = self.client.chat.complete(
            model=self.config.model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ],
            temperature=self.config.temperature,
            response_format={"type": "json_object"},
        )

        usage = TokenUsage(
            prompt_tokens=chat_response.usage.prompt_tokens,
            completion_tokens=chat_response.usage.completion_tokens,
            total_tokens=chat_response.usage.total_tokens,
        )

        cost = ModelPricing.calculate_cost(
            model=self.config.model,
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
        )

        return LLMResponse(
            content=chat_response.choices[0].message.content,
            usage=usage,
            cost=cost,
            model=self.config.model,
            provider=self.name,
        )

    def _execute_chat_stream(
        self,
        prompt: str,
        on_chunk: Callable[[str], None] | None = None,
    ) -> AsyncIterator[tuple[str, int, int]]:
        """
        Execute streaming chat with Mistral.

        Yields:
            (content, prompt_tokens, completion_tokens)
            - content is empty string for final yield with token counts
        """
        response = self.client.chat.stream(
            model=self.config.model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ],
            temperature=self.config.temperature,
        )

        prompt_tokens = 0
        completion_tokens = 0

        for event in response:
            if hasattr(event, "data") and event.data:
                chunk_data = event.data

                if (
                    hasattr(chunk_data, "choices")
                    and chunk_data.choices
                    and len(chunk_data.choices) > 0
                ):
                    delta = chunk_data.choices[0].delta

                    if hasattr(delta, "content") and delta.content:
                        content = delta.content
                        if on_chunk:
                            on_chunk(content)
                        yield (content, 0, 0)

        # Mistral doesn't provide token counts in stream response
        # Estimate based on content length
        yield ("", 0, 0)
