# LLM Local


from core.models import LLMResponse
from core.settings import BaseLLMProvider


class OllamaProvider(BaseLLMProvider):
    def chat(self, prompt: str) -> LLMResponse:
        pass

    def chat_stream(self, prompt: str) -> LLMResponse:
        pass
