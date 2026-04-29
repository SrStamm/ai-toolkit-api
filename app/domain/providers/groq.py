"""
Groq AI provider implementation.

Uses OpenAI-compatible API at https://api.groq.com/openai/v1/.
"""

from collections.abc import AsyncIterator
from typing import Callable
import httpx

from ...domain.models import LLMResponse
from ...domain.providers.retryable_provider import RetryableProvider
from ...domain.providers.base import Message


class GroqProvider(RetryableProvider):
    """
    Groq AI provider using the RetryableProvider base.
    """

    def _setup_provider(self) -> None:
        """Setup Groq-specific attributes."""
        self.name = "groq"
        self.model = self.config.model
        self.api_key = self.config.api_key
        self.base_url = "https://api.groq.com/openai/v1"
        self._timeout = httpx.Timeout(timeout=60.0, connect=10.0, read=None)

    def _get_retryable_exceptions(self) -> tuple[type[Exception], ...]:
        """Groq-specific retryable exceptions."""
        return (
            httpx.TimeoutException,
            httpx.ConnectError,
            httpx.NetworkError,
            httpx.ReadError,
        )

    def _execute_chat_sync(self, prompt: str) -> LLMResponse:
        """Execute synchronous chat with Groq."""
        messages = [{"role": "user", "content": prompt}]
        return self._execute_chat_with_messages(messages)

    def _execute_chat_with_messages(
        self,
        messages: list[Message],
        system_prompt: str | None = None,
    ) -> LLMResponse:
        """Execute synchronous chat with messages using Groq."""
        chat_messages: list[dict] = []

        if system_prompt:
            chat_messages.append({"role": "system", "content": system_prompt})

        chat_messages.extend(messages)

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        data = {
            "model": self.model,
            "messages": chat_messages,
        }

        with httpx.Client(timeout=self._timeout) as client:
            response = client.post(url, headers=headers, json=data)
            response.raise_for_status()
            response_data = response.json()

        content = response_data["choices"][0]["message"]["content"]

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
        on_chunk: Callable[[str], None],
    ) -> AsyncIterator[tuple[str, int, int]]:
        """
        Execute streaming chat with Groq.

        Yields:
            (content, prompt_tokens, completion_tokens)
        """
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        data = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": True,
        }

        accumulated_content = ""
        prompt_tokens = 0
        completion_tokens = 0

        with httpx.Client(timeout=self._timeout) as client:
            with client.stream("POST", url, headers=headers, json=data) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line or not line.startswith("data: "):
                        continue

                    chunk_data = line[6:]  # Remove "data: " prefix
                    if chunk_data == "[DONE]":
                        break

                    import json as json_lib

                    chunk_json = json_lib.loads(chunk_data)
                    delta = chunk_json.get("choices", [{}])[0].get("delta", {}).get(
                        "content", ""
                    )

                    if delta:
                        accumulated_content += delta
                        on_chunk(delta)

                    usage = chunk_json.get("usage", {})
                    if usage.get("prompt_tokens"):
                        prompt_tokens = usage["prompt_tokens"]
                    if usage.get("completion_tokens"):
                        completion_tokens = usage["completion_tokens"]

        yield ("", prompt_tokens, completion_tokens)

    async def _execute_chat_with_messages_stream(
        self,
        messages: list[Message],
        system_prompt: str | None = None,
    ) -> AsyncIterator[tuple[str, LLMResponse | None]]:
        """
        Execute streaming chat with messages using Groq.
        
        Yields (token, final_response).
        """
        chat_messages: list[dict] = []
        
        if system_prompt:
            chat_messages.append({"role": "system", "content": system_prompt})
        
        chat_messages.extend(messages)
        
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        data = {
            "model": self.model,
            "messages": chat_messages,
            "stream": True,
        }
        
        accumulated_content = ""
        prompt_tokens = 0
        completion_tokens = 0
        final_response = None
        
        with httpx.Client(timeout=self._timeout) as client:
            with client.stream("POST", url, headers=headers, json=data) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    
                    chunk_data = line[6:]  # Remove "data: " prefix
                    if chunk_data == "[DONE]":
                        break
                    
                    import json as json_lib
                    chunk_json = json_lib.loads(chunk_data)
                    delta = chunk_json.get("choices", [{}])[0].get("delta", {}).get(
                        "content", ""
                    )
                    
                    if delta:
                        accumulated_content += delta
                        yield (delta, None)
                    
                    usage = chunk_json.get("usage", {})
                    if usage.get("prompt_tokens"):
                        prompt_tokens = usage["prompt_tokens"]
                    if usage.get("completion_tokens"):
                        completion_tokens = usage["completion_tokens"]
        
        final_response = self._build_usage_response(
            content=accumulated_content,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )
        yield ("", final_response)

    async def chat_with_messages_stream(
        self,
        messages: list[Message],
        system_prompt: str | None = None,
    ) -> AsyncIterator[tuple[str, LLMResponse | None]]:
        """
        Stream chat with message history using Groq.
        
        Yields (token, final_response).
        """
        async for token, response in self._execute_chat_with_messages_stream(
            messages, system_prompt
        ):
            yield (token, response)
