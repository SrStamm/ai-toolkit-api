# LLM Local

import random
import time
import asyncio
from typing import AsyncIterator, Optional
import httpx
import structlog
import json

from ..pricing import ModelPricing

from ..models import LLMResponse, TokenUsage
from ..settings import BaseLLMProvider, LLMConfig


class OllamaProvider(BaseLLMProvider):
    def __init__(self, config: LLMConfig):
        self.config = config
        self.name = 'ollama'
        self.model = config.model
        self.logger = structlog.get_logger()



    def _is_retryable_error(self, e: Exception) -> bool:
        return isinstance(
            e,
            (
                httpx.TimeoutException,
                httpx.ConnectError,
                httpx.ConnectError,
                httpx.TimeoutException,
                httpx.NetworkError,
            ),
        )

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

    def chat(self, prompt: str) -> LLMResponse:
        def operation():
            data = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "stream": False,
            }

            estimated_prompt_tokens = 0
            estimated_completion_tokens = 0

            timeout = httpx.Timeout(timeout=10.0, connect=10.0, read=None)

            with httpx.Client() as client:
                url = self.config.url + "/api/chat"
                chat_response = client.post(url, json=data, timeout=timeout)

                data = chat_response.json()

                estimated_prompt_tokens = data.get("prompt_eval_count")
                estimated_completion_tokens = data.get("eval_count")

                delta = data.get("message", {}).get("content", "")

                usage = TokenUsage(
                    prompt_tokens=estimated_prompt_tokens,
                    completion_tokens=estimated_completion_tokens,
                    total_tokens=estimated_completion_tokens + estimated_prompt_tokens,
                )

                cost = ModelPricing.calculate_cost(
                    model="ollama",
                    prompt_tokens=usage.prompt_tokens,
                    completion_tokens=usage.completion_tokens,
                )

                return LLMResponse(
                    content=delta,
                    usage=usage,
                    cost=cost,
                    model=self.config.model,
                    provider="ollama",
                )

        return self._with_retry(operation, model=self.config.model)

    async def chat_stream(self, prompt: str) -> AsyncIterator[tuple[str, Optional[LLMResponse]]]:
        last_exception = None

        data = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }

        estimated_prompt_tokens = 0
        estimated_completion_tokens = 0

        timeout = httpx.Timeout(timeout=10.0, connect=10.0, read=None)

        async with httpx.AsyncClient() as client:
            for attempt in range(self.config.max_retries):
                accumulated_content = ""
                try:
                    url = self.config.url + "/api/chat"
                    async with client.stream("POST", url, json=data, timeout=timeout) as r:
                        async for line in r.aiter_lines():
                            if not line:
                                continue

                            chunk_data = json.loads(line)

                            if chunk_data.get("done"):
                                estimated_prompt_tokens = chunk_data.get("prompt_eval_count")
                                estimated_completion_tokens = chunk_data.get("eval_count")
                                break

                            delta = chunk_data.get("message", {}).get("content", "")

                            if delta:
                                accumulated_content += delta
                                yield (delta, None)

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
                        max_retires=self.config.max_retries,
                        error=str(e),
                        error_type=type(e).__name__,
                    )

                    last_exception = e


                    # If not retryable or last attempt, raise
                    if attempt >= self.config.max_retries - 1:
                        self.logger.error(
                            "all attempts failed",
                            model=self.config.model,
                            total_attempts=self.config.max_retries,
                        )
                        raise last_exception

                    # Waiting before retrying
                    base = 2**attempt
                    jitter = random.uniform(0, 1)
                    sleep_time = base + jitter

                    self.logger.info(
                        "retrying attempt",
                        model=self.config.model,
                        attempt=attempt,
                        seconds=sleep_time,
                    )

                    await asyncio.sleep(sleep_time)


            usage = TokenUsage(
                prompt_tokens=estimated_prompt_tokens,
                completion_tokens=estimated_completion_tokens,
                total_tokens=estimated_prompt_tokens + estimated_completion_tokens,
            )

            cost = ModelPricing.calculate_cost(
                'ollama', usage.prompt_tokens, usage.completion_tokens
            )

            final_response = LLMResponse(
                content=accumulated_content,
                usage=usage,
                cost=cost,
                model=self.config.model,
                provider="ollama",
            )

            # Yield final con metadata completa
            yield ("", final_response)
