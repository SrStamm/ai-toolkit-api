from typing import Dict
from app.domain.models import CostBreakdown


class ModelPricing:
    # Precios por millón de tokens
    PRICES: Dict[str, Dict[str, float]] = {
        # Mistral
        "mistral-small-latest": {"input": 0.1, "output": 0.3},
        "mistral-large-latest": {"input": 2.0, "output": 6.0},
        # Ollama (gratis)
        "ollama": {"input": 0.0, "output": 0.0},
        "qwen2.5:7b": {"input": 0.0, "output": 0.0},
        # Groq
        "llama-3.1-70b-versatile": {"input": 0.65, "output": 0.8},
        "llama-3.1-8b-instant": {"input": 0.05, "output": 0.08},
        "llama-3.3-70b-versatile": {"input": 0.59, "output": 0.79},
        "mixtral-8x7b-32768": {"input": 0.24, "output": 0.24},
    }

    @classmethod
    def get_pricing(cls, model: str) -> Dict[str, float]:
        if model not in cls.PRICES:
            raise ValueError(f"Pricing not configured for model: {model}")
        return cls.PRICES[model]

    @classmethod
    def calculate_cost(
        cls, model: str, prompt_tokens: int, completion_tokens: int
    ) -> CostBreakdown:
        prices = cls.get_pricing(model)
        input_cost = (prompt_tokens / 1_000_000) * prices["input"]
        output_cost = (completion_tokens / 1_000_000) * prices["output"]

        return CostBreakdown(
            input_cost=input_cost,
            output_cost=output_cost,
            total_cost=input_cost + output_cost,
        )
