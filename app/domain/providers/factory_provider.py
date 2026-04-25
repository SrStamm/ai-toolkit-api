"""
Factory para crear proveedores LLM con soporte para overrides en tiempo de ejecución.
"""

from typing import Any

from ...core.settings import LLMConfig
from ...domain.providers.base import BaseLLMProvider
from ...domain.providers.mistral import MistralProvider
from ...domain.providers.ollama import OllamaProvider


class LLMFactory:
    """Factory para crear instancias de providers LLM."""

    _providers: dict[str, type[BaseLLMProvider]] = {
        "ollama": OllamaProvider,
        "mistral": MistralProvider,
    }

    @staticmethod
    def create_provider(
        config: LLMConfig,
        provider_override: str | None = None,
        model_override: str | None = None,
    ) -> BaseLLMProvider:
        """
        Crear una instancia de provider LLM.

        Args:
            config: Configuración base del provider.
            provider_override: Override del provider (ej. "ollama", "mistral").
            model_override: Override del modelo (ej. "llama3", "mistral-small-latest").

        Returns:
            Instancia del provider configurado.
        """
        # Apply overrides to config copy
        overrides: dict[str, Any] = {}
        if provider_override:
            overrides["provider"] = provider_override
        if model_override:
            overrides["model"] = model_override

        config_to_use = (
            config.model_copy(update=overrides) if overrides else config
        )

        provider_name = config_to_use.provider
        provider_class = LLMFactory._providers.get(provider_name)

        if not provider_class:
            raise ValueError(f"Proveedor {provider_name} no soportado")

        return provider_class(config_to_use)
