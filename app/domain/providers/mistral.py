"""
Mistral AI provider implementation using httpx.
"""

from collections.abc import AsyncIterator
from typing import Callable

import httpx

from ...domain.models import LLMResponse
from ...domain.providers.retryable_provider import RetryableProvider
from ...domain.providers.base import Message


class MistralProvider(RetryableProvider):
    """
    Mistral AI provider using httpx directly (no SDK).
    """

    BASE_URL = "https://api.mistral.ai/v1"
    CHAT_COMPLETIONS_ENDPOINT = f"{BASE_URL}/chat/completions"

    def _setup_provider(self) -> None:
        """Setup Mistral-specific attributes."""
        self.name = "mistral"
        self.model = self.config.model
        self.api_key = self.config.api_key
        self._timeout = httpx.Timeout(timeout=60.0, connect=10.0, read=None)

    def _get_retryable_exceptions(self) -> tuple[type[Exception], ...]:
        """Mistral-specific retryable exceptions."""
        return (
            httpx.TimeoutException,
            httpx.ConnectError,
            httpx.NetworkError,
            httpx.ReadError,
        )

    def _execute_chat_sync(self, prompt: str) -> LLMResponse:
        """Execute synchronous chat with Mistral."""
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt},
        ]
        return self._execute_chat_with_messages(messages)

    def _execute_chat_with_messages(
        self,
        messages: list[Message],
        system_prompt: str | None = None,
    ) -> LLMResponse:
        """Execute synchronous chat with messages using Mistral."""
        # Build messages list
        chat_messages: list[dict] = []

        # Add system prompt if provided
        if system_prompt:
            chat_messages.append({"role": "system", "content": system_prompt})

        # Add provided messages
        chat_messages.extend(messages)

        # Request payload
        data = {
            "model": self.model,
            "messages": chat_messages,
            "temperature": self.config.temperature,
            "response_format": {"type": "json_object"},
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        with httpx.Client(timeout=self._timeout) as client:
            response = client.post(
                self.CHAT_COMPLETIONS_ENDPOINT,
                headers=headers,
                json=data,
            )
            response.raise_for_status()
            response_data = response.json()

        # Extract response content
        content = response_data["choices"][0]["message"]["content"]

        # Extract usage info
        usage = response_data.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)

        return self._build_usage_response(
            content=content,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
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
        import json as json_lib

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ],
            "temperature": self.config.temperature,
            "stream": True,
        }

        prompt_tokens = 0
        completion_tokens = 0

        with httpx.Client(timeout=self._timeout) as client:
            with client.stream(
                "POST",
                self.CHAT_COMPLETIONS_ENDPOINT,
                headers=headers,
                json=data,
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line or not line.startswith("data: "):
                        continue

                    chunk_data = line[6:]  # Remove "data: " prefix
                    if chunk_data == "[DONE]":
                        break

                    chunk_json = json_lib.loads(chunk_data)
                    delta = chunk_json.get("choices", [{}])[0].get("delta", {}).get(
                        "content", ""
                    )

                    if delta:
                        if on_chunk:
                            on_chunk(delta)
                        yield (delta, 0, 0)

                    usage = chunk_json.get("usage", {})
                    if usage.get("prompt_tokens"):
                        prompt_tokens = usage["prompt_tokens"]
                    if usage.get("completion_tokens"):
                        completion_tokens = usage["completion_tokens"]

        # Yield final response with token counts
        yield ("", prompt_tokens, completion_tokens)