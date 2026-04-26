"""
Factory para crear proveedores LLM con soporte para overrides en tiempo de ejecución.

Valida provider y model contra la configuración YAML.
"""

import os
from typing import Any

from ...core.settings import LLMConfig, get_settings
from ...domain.providers.base import BaseLLMProvider
from ...domain.providers.groq import GroqProvider
from ...domain.providers.mistral import MistralProvider
from ...domain.providers.ollama import OllamaProvider
from ...domain.exceptions import ProviderNotFoundError, ModelNotFoundError


class LLMFactory:
    """Factory para crear instancias de providers LLM.
    
    Usa la configuración YAML para validar providers y models.
    """

    # Mapeo estático de providers a clases (se valida contra YAML en create_provider)
    _provider_classes: dict[str, type[BaseLLMProvider]] = {
        "ollama": OllamaProvider,
        "mistral": MistralProvider,
        "groq": GroqProvider,
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

        Raises:
            ProviderNotFoundError: Si el provider no está configurado en YAML.
            ModelNotFoundError: Si el model no está configurado para el provider.
        """
        settings = get_settings()
        
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
        model_name = config_to_use.model
        
        # Validar provider contra YAML
        try:
            provider_config = settings.get_provider(provider_name)
        except ProviderNotFoundError as e:
            raise ProviderNotFoundError(f"Provider '{provider_name}' not found in YAML config")
        
        # Validar model contra YAML
        if not model_name:
            # Usar default_model si no se especifica model
            if not provider_config.default_model:
                raise ModelNotFoundError(f"No default model configured for provider '{provider_name}'")
            model_name = provider_config.default_model
            config_to_use = config_to_use.model_copy(update={"model": model_name})
        
        try:
            model_config = settings.get_model(provider_name, model_name)
        except ModelNotFoundError as e:
            raise ModelNotFoundError(f"Model '{model_name}' not found for provider '{provider_name}'")
        
        # Validar que el provider tenga una clase asociada
        provider_class = LLMFactory._provider_classes.get(provider_name)
        if not provider_class:
            raise ProviderNotFoundError(f"Provider '{provider_name}' is not supported by the factory")

        # Get API key: usar la variable de entorno definida en YAML
        api_key = os.getenv(provider_config.api_key_env, "")
        config_to_use = config_to_use.model_copy(update={
            "api_key": api_key,
            "max_tokens": model_config.max_tokens,
        })

        return provider_class(config_to_use)
