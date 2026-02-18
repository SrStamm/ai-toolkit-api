from typing import Optional
from pydantic import BaseModel
import os


class LLMConfig(BaseModel):
    api_key: str
    provider: str
    model: str = "mistral-small-latest"
    temperature: float = 0.0
    max_retries: int = 3
    url: Optional[str] = None

class AppConfig:
    # --- PROVEEDOR PRIMARIO ---
    P_PROVIDER = os.getenv("P_PROVIDER", "mistral")
    P_API_KEY = os.getenv("P_API_KEY")
    P_MODEL = os.getenv("P_MODEL", "mistral-small-latest")
    P_URL = os.getenv("P_URL")

    # --- PROVEEDOR FALLBACK ---
    F_PROVIDER = os.getenv("F_PROVIDER", "ollama")
    F_API_KEY = os.getenv("F_API_KEY", "")
    F_MODEL = os.getenv("F_MODEL", "qwen2.5:7b")
    F_URL = os.getenv("F_URL", "http://host.docker.internal:11434")

    @classmethod
    def get_primary_config(cls) -> LLMConfig:
        return LLMConfig(
            provider=cls.P_PROVIDER,
            api_key=cls.P_API_KEY,
            model=cls.P_MODEL,
            url=cls.P_URL
        )

    @classmethod
    def get_fallback_config(cls) -> LLMConfig:
        return LLMConfig(
            provider=cls.F_PROVIDER,
            api_key=cls.F_API_KEY,
            model=cls.F_MODEL,
            url=cls.F_URL
        )
