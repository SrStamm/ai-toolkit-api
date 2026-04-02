"""
Configuración de la aplicación usando pydantic-settings.

Permite validación de tipos, múltiples entornos, y mejor DX.
"""

from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMConfig(BaseSettings):
    """Configuración para un proveedor LLM."""

    api_key: str = Field(default="")
    provider: str = Field(default="mistral")
    model: str = Field(default="mistral-small-latest")
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    max_retries: int = Field(default=3, ge=1, le=10)
    url: str | None = Field(default=None)

    model_config = SettingsConfigDict(
        env_prefix="",
        env_nested_delimiter="__",
    )


class AppSettings(BaseSettings):
    """Configuración principal de la aplicación."""

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
    f_url: str = Field(default="http://host.docker.internal:11434")

    # Redis
    redis_url: str | None = Field(default=None)
    redis_host: str = Field(default="localhost")
    redis_port: int = Field(default=6379)
    redis_db: int = Field(default=0)

    # Qdrant
    qdrant_host: str = Field(default="qdrant")
    qdrant_port: int = Field(default=6333)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    def get_primary_llm_config(self) -> LLMConfig:
        """Get primary LLM provider configuration."""
        return LLMConfig(
            provider=self.p_provider,
            api_key=self.p_api_key,
            model=self.p_model,
            url=self.p_url,
        )

    def get_fallback_llm_config(self) -> LLMConfig:
        """Get fallback LLM provider configuration."""
        return LLMConfig(
            provider=self.f_provider,
            api_key=self.f_api_key,
            model=self.f_model,
            url=self.f_url,
            max_retries=5,  # More retries for fallback
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


# Alias para backwards compatibility
AppConfig = AppSettings


def get_primary_config() -> LLMConfig:
    """Get primary LLM config. Deprecated - use get_settings().get_primary_llm_config()"""
    return get_settings().get_primary_llm_config()


def get_fallback_config() -> LLMConfig:
    """Get fallback LLM config. Deprecated - use get_settings().get_fallback_llm_config()"""
    return get_settings().get_fallback_llm_config()
