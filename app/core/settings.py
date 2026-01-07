from abc import ABC, abstractmethod
from mistralai import Mistral
from pydantic import BaseModel
import time


class LLMConfig(BaseModel):
    api_key: str
    model: str = "mistral-small-latest"
    temperature: float = 0.0
    max_retries: int = 3


class BaseLLMProvider(ABC):
    @abstractmethod
    def chat(self, prompt: str) -> str:
        pass


class MistralProvider(BaseLLMProvider):
    def __init__(self, config: LLMConfig):
        self.config = config
        self.client = Mistral(api_key=self.config.api_key)

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
                return chat_response.choices[0].message.content
            except Exception as e:
                if attempt == self.config.max_retries - 1:
                    raise e
                time.sleep(2**attempt)
        raise ValueError("Failed to generate content after retries.")
