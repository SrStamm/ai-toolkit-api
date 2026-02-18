from .mistral import MistralProvider
from .ollama import OllamaProvider
from ...core.settings import LLMConfig

class LLMFactory:
    _providers = {
        "ollama": OllamaProvider,
        "mistral": MistralProvider
    }

    @staticmethod
    def create_provider(config: LLMConfig):
        provider_class = LLMFactory._providers.get(config.provider)

        if not provider_class:
            raise ValueError(f"Proveedor {config.provider} no soportado")

        return provider_class(config)
