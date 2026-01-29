from .models import LLMResponse
from pydantic import BaseModel, ValidationError
from .custom_logging import time_response
from .settings import LLMConfig, MistralProvider, BaseLLMProvider
from dotenv import load_dotenv
import os

load_dotenv()


class LLMClient:
    def __init__(self, provider: BaseLLMProvider):
        self.provider = provider

    @time_response
    def generate_content(self, prompt: str) -> LLMResponse[str]:
        return self.provider.chat(prompt)

    @time_response
    def generate_structured_output(
        self, prompt: str, output_schema: type[BaseModel]
    ) -> LLMResponse[BaseModel]:
        structured_prompt = f"{prompt}\n Output como JSON válido, únicamente devuelve el objeto JSON, conforme a este schema: {output_schema.model_json_schema()}"

        response = self.provider.chat(structured_prompt)

        try:
            parsed_content = output_schema.model_validate_json(response)

            return LLMResponse(
                content=parsed_content,
                usage=response.usage,
                cost=response.cost,
                model=response.model,
                provider=response.provider,
            )
        except ValidationError:
            error_prompt = f"{structured_prompt}\nPrevious output invalid. Corrige: {response.content}"
            return self.generate_structured_output(error_prompt, output_schema)


def get_llm_client():
    API_KEY = os.getenv("MISTRAL_API_KEY")
    if not API_KEY:
        raise ValueError("API_KEY no configurada")

    config = LLMConfig(api_key=API_KEY)
    provider = MistralProvider(config)
    return LLMClient(provider)
