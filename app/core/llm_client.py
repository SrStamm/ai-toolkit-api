from pydantic import BaseModel, ValidationError
from .settings import LLMConfig, MistralProvider, BaseLLMProvider
from dotenv import load_dotenv
import os

load_dotenv()


class LLMClient:
    def __init__(self, provider: BaseLLMProvider):
        self.provider = provider

    def generate_content(self, prompt: str) -> str:
        return self.provider.chat(prompt)

    def generate_structured_output(
        self, prompt: str, output_schema: type[BaseModel]
    ) -> BaseModel:
        """Para Feature 1: Extrae estructurado con validation y retry."""
        structured_prompt = f"{prompt}\n Output como JSON válido, únicamente devuelve el objeto JSON, conforme a este schema: {output_schema.model_json_schema()}"
        response_text = self.provider.chat(structured_prompt)
        try:
            return output_schema.model_validate_json(response_text)
        except ValidationError:
            # Retry con corrección: Agrega al prompt el error
            error_prompt = f"{structured_prompt}\nPrevious output invalid. Corrige: {response_text}"
            return self.generate_structured_output(
                error_prompt, output_schema
            )  # Recursivo, limita profundidad si quieres


def get_llm_client():
    API_KEY = os.getenv("MISTRAL_API_KEY")
    if not API_KEY:
        raise ValueError("API_KEY no configurada")

    config = LLMConfig(api_key=API_KEY)
    provider = MistralProvider(config)
    return LLMClient(provider)
