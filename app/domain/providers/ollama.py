"""
Ollama local LLM provider implementation.
"""

import json
from typing import Callable
import httpx

from app.core.settings import LLMConfig
from app.domain.models import LLMResponse, TokenUsage
from app.domain.services.pricing import ModelPricing
from app.domain.providers.retryable_provider import RetryableProvider


class OllamaProvider(RetryableProvider):
    """
    Ollama local LLM provider using the RetryableProvider base.
    """

    def _setup_provider(self) -> None:
        """Setup Ollama-specific attributes."""
        self.name = "ollama"
        self.model = self.config.model
        self.url = self.config.url or "http://localhost:11434"
        self._timeout = httpx.Timeout(timeout=60.0, connect=10.0, read=None)

    def _get_retryable_exceptions(self) -> tuple[type[Exception], ...]:
        """Ollama-specific retryable exceptions."""
        return (
            httpx.TimeoutException,
            httpx.ConnectError,
            httpx.NetworkError,
        )

    async def _execute_chat_stream(
        self,
        prompt: str,
        on_chunk: Callable[[str], None],
    ) -> tuple[str, int, int]:
        """
        Execute streaming chat with Ollama.

        Returns:
            tuple of (accumulated_content, prompt_tokens, completion_tokens)
        """
        accumulated_content = ""
        prompt_tokens = 0
        completion_tokens = 0

        data = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
        }

        url = f"{self.url}/api/chat"

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            async with client.stream("POST", url, json=data) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue

                    chunk_data = json.loads(line)

                    if chunk_data.get("done"):
                        prompt_tokens = chunk_data.get("prompt_eval_count", 0)
                        completion_tokens = chunk_data.get("eval_count", 0)
                        break

                    delta = chunk_data.get("message", {}).get("content", "")

                    if delta:
                        accumulated_content += delta
                        on_chunk(delta)

        return (accumulated_content, prompt_tokens, completion_tokens)

    def _execute_chat_sync(self, prompt: str) -> LLMResponse:
        """Execute synchronous chat with Ollama."""
        data = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        }

        url = f"{self.url}/api/chat"

        with httpx.Client(timeout=self._timeout) as client:
            response = client.post(url, json=data)
            response.raise_for_status()
            data = response.json()

        prompt_tokens = data.get("prompt_eval_count", 0)
        completion_tokens = data.get("eval_count", 0)
        content = data.get("message", {}).get("content", "")

        return self._build_usage_response(
            content=content,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )
