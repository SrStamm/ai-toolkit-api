from typing import AsyncIterator, Optional
import random

from ..models import LLMResponse, TokenUsage
from ..pricing import ModelPricing
from ..settings import BaseLLMProvider, LLMConfig
from mistralai import Mistral
import time
import structlog


class MistralProvider(BaseLLMProvider):
    def __init__(self, config: LLMConfig):
        self.config = config
        self.client = Mistral(api_key=self.config.api_key)
        self.logger = structlog.get_logger()

    def _is_retryable_error(self, e: Exception) -> bool:
        return isinstance(e, (TimeoutError, ConnectionError))

    def _with_retry(self, operation, *, model: str):
        for attempt in range(self.config.max_retries):
            try:
                return operation()
            except Exception as e:
                if not self._is_retryable_error(e):
                    raise

                if attempt == self.config.max_retries - 1:
                    raise

                base = 2**attempt
                jitter = random.uniform(0, 1)

                self.logger.info(
                    "llm_retry",
                    model=model,
                    attempt=attempt,
                    error=str(e),
                    sleep=base + jitter,
                )

                time.sleep(base + jitter)

    # Send a chat prompt with data and receive a JSON object response
    def chat(self, prompt: str) -> LLMResponse:
        def operation():
            chat_response = self.client.chat.complete(
                model=self.config.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant.",
                    },
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
                provider="mistral",
            )

        return self._with_retry(operation, model=self.config.model)

    async def chat_stream(
        self, prompt: str
    ) -> AsyncIterator[tuple[str, Optional[LLMResponse]]]:
        accumulated_content = ""
        last_exception = None

        for attempt in range(self.config.max_retries):
            try:
                response = self.client.chat.stream(
                    model=self.config.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a helpful assistant.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    temperature=self.config.temperature,
                )

                # Stream chunks
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
                                accumulated_content += content
                                yield (content, None)
            except ValueError as e:
                # Fail but have partial output
                if accumulated_content:
                    self.logger.warning(
                        "stream_failed_after_partial_output",
                        model=self.config.model,
                        attempt=attempt,
                    )
                    raise

                # Fail
                self.logger.info(
                    "attempt failed",
                    model=self.config.model,
                    attempt=attempt,
                    error=str(e),
                )

                last_exception = e

                # If not retryable or last attempt, raise
                if attempt < self.config.max_retries - 1:
                    base = 2**attempt
                    jitter = random.uniform(0, 1)

                    self.logger.info(
                        "retrying attempt",
                        model=self.config.model,
                        attempt=attempt,
                        seconds=base + jitter,
                    )
                    last_exception = e
                    time.sleep(base + jitter)

                else:
                    self.logger.error("all attempts failed", model=self.config.model)
                    raise last_exception

        estimated_prompt_tokens = len(prompt) // 4
        estimated_completion_tokens = len(accumulated_content) // 4

        usage = TokenUsage(
            prompt_tokens=estimated_prompt_tokens,
            completion_tokens=estimated_completion_tokens,
            total_tokens=estimated_prompt_tokens + estimated_completion_tokens,
        )

        cost = ModelPricing.calculate_cost(
            self.config.model, usage.prompt_tokens, usage.completion_tokens
        )

        final_response = LLMResponse(
            content=accumulated_content,
            usage=usage,
            cost=cost,
            model=self.config.model,
            provider="mistral",
        )

        self.logger.info(
            "stream_completed",
            model=self.config.model,
            tokens=usage.total_tokens,
            cost_usd=f"${cost.total_cost:.6f}",
            estimation="simple",
        )

        # Yield final con metadata completa
        yield ("", final_response)
