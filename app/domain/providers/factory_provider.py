from app.domain.providers.mistral import MistralProvider
from app.domain.providers.ollama import OllamaProvider
from app.core.settings import LLMConfig


class LLMFactory:
    _providers = {"ollama": OllamaProvider, "mistral": MistralProvider}

    @staticmethod
    def create_provider(config: LLMConfig):
        provider_class = LLMFactory._providers.get(config.provider)

        if not provider_class:
            raise ValueError(f"Proveedor {config.provider} no soportado")

        return provider_class(config)
