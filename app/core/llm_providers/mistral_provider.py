from typing import AsyncIterator, Optional
from ..models import LLMResponse, TokenUsage
from ..pricing import ModelPricing
from ..settings import BaseLLMProvider, LLMConfig
from mistralai import Mistral
import time
import structlog

logger = structlog.get_logger()


class MistralProvider(BaseLLMProvider):
    def __init__(self, config: LLMConfig):
        self.config = config
        self.client = Mistral(api_key=self.config.api_key)

    # Send a chat prompt with data and receive a JSON object response
    def chat(self, prompt: str) -> LLMResponse:
        for attempt in range(self.config.max_retries):
            try:
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

                content = chat_response.choices[0].message.content
                usage = chat_response.usage

                usage = TokenUsage(
                    prompt_tokens=usage.prompt_tokens,
                    completion_tokens=usage.completion_tokens,
                    total_tokens=usage.total_tokens,
                )

                cost = ModelPricing.calculate_cost(
                    model=self.config.model,
                    prompt_tokens=usage.prompt_tokens,
                    completion_tokens=usage.completion_tokens,
                )

                return LLMResponse(
                    content=content,
                    usage=usage,
                    cost=cost,
                    model=self.config.model,
                    provider="mistral",
                )

            except Exception as e:
                if attempt == self.config.max_retries - 1:
                    raise e
                time.sleep(2**attempt)

        raise ValueError("Failed to generate content after retries.")

    async def chat_stream(
        self, prompt: str
    ) -> AsyncIterator[tuple[str, Optional[LLMResponse]]]:
        accumulated_content = ""

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

        logger.info(
            "stream_completed",
            model=self.config.model,
            tokens=usage.total_tokens,
            cost_usd=f"${cost.total_cost:.6f}",
            estimation="simple",
        )

        # Yield final con metadata completa
        yield ("", final_response)
