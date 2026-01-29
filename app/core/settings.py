from abc import ABC, abstractmethod
from .models import LLMResponse, TokenUsage
from .pricing import ModelPricing
from mistralai import Mistral
from pydantic import BaseModel
import time
import structlog


class LLMConfig(BaseModel):
    api_key: str
    model: str = "mistral-small-latest"
    temperature: float = 0.0
    max_retries: int = 3


class BaseLLMProvider(ABC):
    @abstractmethod
    def chat(self, prompt: str) -> LLMResponse:
        pass


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
                            "content": "You are a data extractor. Output ONLY pure JSON.",
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
