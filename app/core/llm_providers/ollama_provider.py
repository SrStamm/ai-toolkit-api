# LLM Local

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
        self.model = config.model
        self.logger = structlog.get_logger()
        self.url = "http://ollama:11434"

    def chat(self, prompt: str) -> LLMResponse:
        pass

    async def chat_stream(self, prompt: str) -> AsyncIterator[tuple[str, Optional[LLMResponse]]]:
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

        async with httpx.AsyncClient() as client:
            accumulated_content = ""
            async with client.stream("POST", self.url + '/api/chat', json=data, timeout=None) as r:
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

                    print(line)


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
