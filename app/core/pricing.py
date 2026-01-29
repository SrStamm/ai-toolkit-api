from typing import Dict
from .models import CostBreakdown


class ModelPricing:
    # Precios por millón de tokens
    PRICES: Dict[str, Dict[str, float]] = {
        "mistral-small-latest": {"input": 0.1, "output": 0.3},
        "mistral-large-latest": {"input": 2.0, "output": 6.0},
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
