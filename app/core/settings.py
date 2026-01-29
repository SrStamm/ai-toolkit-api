from abc import ABC, abstractmethod
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
    def chat(self, prompt: str) -> str:
        pass


logger = structlog.get_logger()


class MistralProvider(BaseLLMProvider):
    def __init__(self, config: LLMConfig):
        self.config = config
        self.client = Mistral(api_key=self.config.api_key)
        self.prices = {"input": 0.1, "output": 0.3}

    # Send a chat prompt with data and receive a JSON object response
    def chat(self, prompt: str):
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

                promp_t = usage.prompt_tokens
                comp_t = usage.completion_tokens
                total_t = usage.total_tokens

                cost_input = (promp_t / 1_000_000) * self.prices["input"]
                cost_output = (comp_t / 1_000_000) * self.prices["output"]
                total_cost = cost_input + cost_output

                logger.info(
                    "Tokens",
                    promp_t=promp_t,
                    comp_t=comp_t,
                    total_cost=f"{total_cost:.6f}",
                )

                return content
            except Exception as e:
                if attempt == self.config.max_retries - 1:
                    raise e
                time.sleep(2**attempt)
        raise ValueError("Failed to generate content after retries.")
