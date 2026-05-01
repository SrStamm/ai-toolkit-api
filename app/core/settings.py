"""
Configuración de la aplicación usando pydantic-settings.

Permite validación de tipos, múltiples entornos, y mejor DX.
Incluye carga de proveedores y modelos desde YAML.
"""

import os
from functools import lru_cache
from typing import Optional

import yaml
from pydantic import BaseModel, Field, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.domain.exceptions import ProviderNotFoundError, ModelNotFoundError


class LLMConfig(BaseSettings):
    """Configuración para un proveedor LLM."""

    api_key: str = Field(default="")
    provider: str = Field(default="mistral")
    model: str = Field(default="mistral-small-latest")
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    max_retries: int = Field(default=3, ge=1, le=10)
    max_tokens: int | None = Field(default=None)
    url: str | None = Field(default=None)

    model_config = SettingsConfigDict(
        env_prefix="",
        env_nested_delimiter="__",
        extra="ignore",
    )


class ModelConfig(BaseModel):
    """Configuración de un modelo de LLM."""

    name: str = Field(..., description="Nombre del modelo")
    max_tokens: int = Field(..., gt=0, description="Máximo número de tokens soportados por el modelo")
    supports_tools: bool = Field(..., description="Indica si el modelo soporta herramientas (tools)")


class ProviderConfig(BaseModel):
    """Configuración de un proveedor de LLM."""

    name: str = Field(..., description="Nombre del proveedor")
    api_key_env: str = Field(
        ...,
        description="Nombre de la variable de entorno que contiene la API key del proveedor",
    )
    default_model: Optional[str] = Field(
        None,
        description="Modelo por defecto para el proveedor. Debe existir en la lista de models.",
    )
    models: list[ModelConfig] = Field(..., description="Lista de modelos soportados por el proveedor")

    def validate_default_model(self) -> None:
        """Validar que el default_model exista en la lista de models."""
        if self.default_model and self.default_model not in [model.name for model in self.models]:
            raise ValueError(f"default_model '{self.default_model}' not found in models")


class YamlAppConfig(BaseModel):
    """Configuración principal de proveedores y modelos (cargada desde YAML)."""

    providers: list[ProviderConfig] = Field(..., description="Lista de proveedores de LLM")

    @field_validator("providers")
    @classmethod
    def validate_provider_names(cls, v: list[ProviderConfig]) -> list[ProviderConfig]:
        """Validar que los nombres de los proveedores sean únicos."""
        names = [provider.name for provider in v]
        if len(names) != len(set(names)):
            raise ValueError("Provider names must be unique")
        return v


def get_provider_from_config(config: YamlAppConfig, provider_name: str) -> ProviderConfig:
    """Obtener configuración de un proveedor por nombre."""
    for provider in config.providers:
        if provider.name == provider_name:
            return provider
    raise ProviderNotFoundError(f"Provider '{provider_name}' not found in YAML config")


def get_model_from_config(config: YamlAppConfig, provider_name: str, model_name: str) -> ModelConfig:
    """Obtener configuración de un modelo por nombre y proveedor."""
    provider = get_provider_from_config(config, provider_name)
    for model in provider.models:
        if model.name == model_name:
            return model
    raise ModelNotFoundError(f"Model '{model_name}' not found for provider '{provider_name}'")


class AppSettings(BaseSettings):
    """Configuración principal de la aplicación.

    Incluye proveedores y modelos cargados desde YAML.
    """

    # Environment
    environment: str = Field(default="development")
    debug: bool = Field(default=False)

    # CORS
    allowed_origins: str = Field(
        default="http://localhost:8000,http://localhost:8080,http://localhost:5173",
        description="Comma-separated list of allowed CORS origins",
    )

    # Primary LLM Provider (P_)
    p_provider: str = Field(default="mistral")
    p_api_key: str = Field(default="")
    p_model: str = Field(default="mistral-small-latest")
    p_url: str | None = Field(default=None)

    # Fallback LLM Provider (F_)
    f_provider: str = Field(default="ollama")
    f_api_key: str = Field(default="")
    f_model: str = Field(default="qwen2.5:7b")
    f_url: str | None = Field(default="http://host.docker.internal:11434")

    # Redis
    redis_url: str | None = Field(default=None)
    redis_host: str = Field(default="localhost")
    redis_port: int = Field(default=6379)
    redis_db: int = Field(default=0)

    # Qdrant
    qdrant_host: str = Field(default="qdrant")
    qdrant_port: int = Field(default=6333)

    # YAML config (no se expone como variable de entorno)
    _yaml_config: Optional[YamlAppConfig] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    def __init__(self, **kwargs):
        """Inicializar configuración y cargar YAML."""
        super().__init__(**kwargs)
        self._load_yaml_config()

    def _load_yaml_config(self) -> None:
        """Cargar y validar configuración YAML de proveedores y modelos."""
        yaml_path = os.path.join(os.path.dirname(__file__), "../config/providers.yaml")
        try:
            with open(yaml_path, "r") as f:
                yaml_data = yaml.safe_load(f)
            self._yaml_config = YamlAppConfig(**yaml_data)

            # Validar default_model para cada provider
            for provider in self._yaml_config.providers:
                provider.validate_default_model()

            # Validar que los proveedores configurados en .env existan en YAML
            self._validate_env_providers()

        except FileNotFoundError:
            raise FileNotFoundError(f"YAML config file not found: {yaml_path}")
        except ValidationError as e:
            raise ValueError(f"Invalid YAML config: {e}")

    def get_provider(self, provider_name: str) -> ProviderConfig:
        """Obtener configuración de un proveedor por nombre."""
        return get_provider_from_config(self._yaml_config, provider_name)

    def get_model(self, provider_name: str, model_name: str) -> ModelConfig:
        """Obtener configuración de un modelo por nombre y proveedor."""
        return get_model_from_config(self._yaml_config, provider_name, model_name)

    def _validate_env_providers(self) -> None:
        """Validar que los proveedores configurados en .env existan en YAML."""
        # Validar primary provider
        try:
            self.get_provider(self.p_provider)
        except ProviderNotFoundError:
            raise ValueError(f"Primary provider '{self.p_provider}' not found in YAML config")

        # Validar fallback provider
        try:
            self.get_provider(self.f_provider)
        except ProviderNotFoundError:
            raise ValueError(f"Fallback provider '{self.f_provider}' not found in YAML config")

    @property
    def yaml_config(self) -> YamlAppConfig:
        """Obtener la configuración YAML."""
        if not self._yaml_config:
            raise ValueError("YAML config not loaded")
        return self._yaml_config

    def get_primary_llm_config(self) -> LLMConfig:
        """Get primary LLM provider configuration.

        Usa la configuración YAML para validar provider y model.
        """
        provider_config = self.get_provider(self.p_provider)

        # Usar default_model si no se especifica model
        model_name = self.p_model
        if not model_name and provider_config.default_model:
            model_name = provider_config.default_model

        model_config = self.get_model(self.p_provider, model_name)

        return LLMConfig(
            provider=self.p_provider,
            api_key=self.p_api_key,
            model=model_name,
            url=self.p_url,
            max_tokens=model_config.max_tokens,
        )

    def get_fallback_llm_config(self) -> LLMConfig:
        """Get fallback LLM provider configuration.

        Usa la configuración YAML para validar provider y model.
        """
        provider_config = self.get_provider(self.f_provider)

        # Usar default_model si no se especifica model
        model_name = self.f_model
        if not model_name and provider_config.default_model:
            model_name = provider_config.default_model

        model_config = self.get_model(self.f_provider, model_name)

        return LLMConfig(
            provider=self.f_provider,
            api_key=self.f_api_key,
            model=model_name,
            url=self.f_url,
            max_retries=5,  # More retries for fallback
            max_tokens=model_config.max_tokens,
        )

    def get_allowed_origins(self) -> list[str]:
        """Get list of allowed CORS origins."""
        return [
            origin.strip()
            for origin in self.allowed_origins.split(",")
            if origin.strip()
        ]

    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment.lower() in ("production", "prod")


@lru_cache
def get_settings() -> AppSettings:
    """Get cached settings instance."""
    return AppSettings()


def get_primary_config() -> LLMConfig:
    """Get primary LLM config. Deprecated - use get_settings().get_primary_llm_config()"""
    return get_settings().get_primary_llm_config()


def get_fallback_config() -> LLMConfig:
    """Get fallback LLM config. Deprecated - use get_settings().get_fallback_llm_config()"""
    return get_settings().get_fallback_llm_config()
