# LLM Local


from ..models import LLMResponse
from ..settings import BaseLLMProvider


class OllamaProvider(BaseLLMProvider):
    def chat(self, prompt: str) -> LLMResponse:
        pass

    def chat_stream(self, prompt: str) -> LLMResponse:
        pass
