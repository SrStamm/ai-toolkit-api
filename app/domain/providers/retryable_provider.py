"""
RetryableProvider base con lógica de retry común.

Reduce duplicación entre providers (Mistral, Ollama, etc).
"""

import random
import time
import asyncio
from abc import abstractmethod
from typing import Callable, TypeVar
from collections.abc import AsyncIterator
import structlog

from app.domain.models import LLMResponse, TokenUsage
from app.domain.services.pricing import ModelPricing
from app.core.settings import LLMConfig
from app.domain.providers.base import BaseLLMProvider, Message
from app.domain.exceptions import (
    RetryableError,
    NetworkTimeoutError,
    ConnectionError as LLMConnectionError,
)

T = TypeVar("T")
logger = structlog.get_logger()


class RetryableProvider(BaseLLMProvider):
    """
    Provider base con retry logic común.

    Subclasses deben implementar:
    - _get_retryable_exceptions() -> tuple[type[Exception], ...]
    - _execute_chat_sync(prompt: str) -> LLMResponse
    - _execute_chat_stream(prompt: str) -> AsyncIterator[tuple[str, LLMResponse | None]]
    """

    def __init__(self, config: LLMConfig):
        self.config = config
        self.logger = structlog.get_logger()
        self._setup_provider()

    def _setup_provider(self) -> None:
        """Setup provider-specific attributes (name, client, etc). Override in subclass."""
        self.name = "unknown"
        self.model = self.config.model

    @abstractmethod
    def _get_retryable_exceptions(self) -> tuple[type[Exception], ...]:
        """Return tuple of exception types that should trigger retry."""
        ...

    @abstractmethod
    def _execute_chat_sync(self, prompt: str) -> LLMResponse:
        """Execute synchronous chat. Implement in subclass."""
        ...

    @abstractmethod
    def _execute_chat_with_messages(
        self,
        messages: list[Message],
        system_prompt: str | None = None,
    ) -> LLMResponse:
        """
        Execute synchronous chat with messages. Implement in subclass.
        """
        ...

    @abstractmethod
    def _execute_chat_stream(
        self,
        prompt: str,
        on_chunk: Callable[[str], None],
    ) -> tuple[str, int, int]:
        """
        Execute streaming chat.

        Returns:
            tuple of (accumulated_content, prompt_tokens, completion_tokens)
        """
        ...

    def _is_retryable_error(self, e: Exception) -> bool:
        """Check if exception is retryable."""
        return isinstance(e, self._get_retryable_exceptions())

    def _with_retry_sync(self, operation: Callable[[], T]) -> T:
        """Execute sync operation with exponential backoff retry."""
        last_exception: Exception | None = None

        for attempt in range(self.config.max_retries):
            try:
                return operation()
            except Exception as e:
                last_exception = e

                if not self._is_retryable_error(e):
                    self.logger.error(
                        "non_retryable_error",
                        error=str(e),
                        error_type=type(e).__name__,
                    )
                    raise

                if attempt == self.config.max_retries - 1:
                    self.logger.error(
                        "all_retry_attempts_exhausted",
                        model=self.config.model,
                        total_attempts=self.config.max_retries,
                        error=str(e),
                    )
                    raise last_exception

                base = 2**attempt
                jitter = random.uniform(0, 1)
                sleep_time = base + jitter

                self.logger.info(
                    "llm_retry",
                    model=self.config.model,
                    attempt=attempt,
                    error=str(e),
                    sleep=sleep_time,
                )

                time.sleep(sleep_time)

        raise last_exception or RuntimeError("Unexpected retry loop exit")

    def chat(self, prompt: str) -> LLMResponse:
        """Synchronous chat with retry."""
        return self._with_retry_sync(lambda: self._execute_chat_sync(prompt))

    def chat_with_messages(
        self,
        messages: list[Message],
        system_prompt: str | None = None,
    ) -> LLMResponse:
        """
        Synchronous chat with message history and optional system prompt.
        """
        return self._with_retry_sync(
            lambda: self._execute_chat_with_messages(messages, system_prompt)
        )

    async def _with_retry_async(
        self, operation: Callable[[], AsyncIterator[tuple[str, T]]]
    ) -> tuple[str, int, int]:
        """Execute async streaming operation with exponential backoff retry."""
        accumulated_content = ""
        prompt_tokens = 0
        completion_tokens = 0

        for attempt in range(self.config.max_retries):
            accumulated_content = ""
            try:
                async for content, p_tokens, c_tokens in operation():
                    if content:
                        accumulated_content += content
                        yield (content, 0, 0)
                    if p_tokens > 0:
                        prompt_tokens = p_tokens
                    if c_tokens > 0:
                        completion_tokens = c_tokens
                break

            except Exception as e:
                if not self._is_retryable_error(e):
                    self.logger.error(
                        "non_retryable_error",
                        model=self.config.model,
                        error=str(e),
                        error_type=type(e).__name__,
                    )
                    raise

                # Fail but have partial output
                if accumulated_content:
                    self.logger.error(
                        "stream_failed_after_partial_output",
                        model=self.config.model,
                        attempt=attempt + 1,
                        error=str(e),
                        partial_length=len(accumulated_content),
                    )
                    raise

                # Fail
                self.logger.warning(
                    "stream_attempt_failed",
                    model=self.config.model,
                    attempt=attempt + 1,
                    max_retries=self.config.max_retries,
                    error=str(e),
                    error_type=type(e).__name__,
                )

                if attempt >= self.config.max_retries - 1:
                    self.logger.error(
                        "all_retry_attempts_exhausted",
                        model=self.config.model,
                        total_attempts=self.config.max_retries,
                    )
                    raise

                base = 2**attempt
                jitter = random.uniform(0, 1)
                sleep_time = base + jitter

                self.logger.info(
                    "retrying_attempt",
                    model=self.config.model,
                    attempt=attempt,
                    seconds=sleep_time,
                )

                await asyncio.sleep(sleep_time)

        yield ("", prompt_tokens, completion_tokens)

    async def chat_stream(
        self, prompt: str
    ) -> AsyncIterator[tuple[str, LLMResponse | None]]:
        """Streaming chat with retry."""
        accumulated_content = ""
        prompt_tokens = 0
        completion_tokens = 0

        for attempt in range(self.config.max_retries):
            accumulated_content = ""
            prompt_tokens = 0
            completion_tokens = 0

            try:
                async for content, p_tokens, c_tokens in self._execute_chat_stream(
                    prompt
                ):
                    if content:
                        accumulated_content += content
                        yield (content, None)
                    if p_tokens > 0:
                        prompt_tokens = p_tokens
                    if c_tokens > 0:
                        completion_tokens = c_tokens
                break

            except Exception as e:
                if not self._is_retryable_error(e):
                    self.logger.error(
                        "non_retryable_error",
                        model=self.config.model,
                        error=str(e),
                        error_type=type(e).__name__,
                    )
                    raise

                if accumulated_content:
                    self.logger.error(
                        "stream_failed_after_partial_output",
                        model=self.config.model,
                        attempt=attempt + 1,
                        error=str(e),
                        partial_length=len(accumulated_content),
                    )
                    raise

                self.logger.warning(
                    "stream_attempt_failed",
                    model=self.config.model,
                    attempt=attempt + 1,
                    max_retries=self.config.max_retries,
                    error=str(e),
                )

                if attempt >= self.config.max_retries - 1:
                    self.logger.error(
                        "all_retry_attempts_exhausted",
                        model=self.config.model,
                        total_attempts=self.config.max_retries,
                    )
                    raise

                base = 2**attempt
                jitter = random.uniform(0, 1)
                sleep_time = base + jitter

                await asyncio.sleep(sleep_time)

        # Yield final response with metadata
        usage = TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        )

        cost = ModelPricing.calculate_cost(
            self.config.model,
            usage.prompt_tokens,
            usage.completion_tokens,
        )

        final_response = LLMResponse(
            content=accumulated_content,
            usage=usage,
            cost=cost,
            model=self.config.model,
            provider=self.name,
        )

        yield ("", final_response)

    def _build_usage_response(
        self,
        content: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> LLMResponse:
        """Build LLMResponse from usage data."""
        usage = TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        )

        cost = ModelPricing.calculate_cost(
            self.config.model,
            usage.prompt_tokens,
            usage.completion_tokens,
        )

        return LLMResponse(
            content=content,
            usage=usage,
            cost=cost,
            model=self.config.model,
            provider=self.name,
        )
