"""
Factory para crear proveedores LLM con soporte para overrides en tiempo de ejecución.
"""

import os
from typing import Any

from ...core.settings import LLMConfig
from ...domain.providers.base import BaseLLMProvider
from ...domain.providers.groq import GroqProvider
from ...domain.providers.mistral import MistralProvider
from ...domain.providers.ollama import OllamaProvider


class LLMFactory:
    """Factory para crear instancias de providers LLM."""

    _providers: dict[str, type[BaseLLMProvider]] = {
        "ollama": OllamaProvider,
        "mistral": MistralProvider,
        "groq": GroqProvider,
    }

    # Mapping provider -> env var para API key
    _api_key_env_vars: dict[str, str] = {
        "mistral": "MISTRAL_API_KEY",
        "groq": "GROQ_API_KEY",
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

        # Get API key: if provider_override, always use env var for that provider
        # otherwise use config.api_key if set, otherwise fallback to env var
        api_key = config_to_use.api_key
        if provider_override:
            env_var = LLMFactory._api_key_env_vars.get(provider_override)
            if env_var:
                api_key = os.getenv(env_var, "")
        elif not api_key:
            env_var = LLMFactory._api_key_env_vars.get(provider_name)
            if env_var:
                api_key = os.getenv(env_var, "")

        config_to_use = config_to_use.model_copy(update={"api_key": api_key})

        return provider_class(config_to_use)
