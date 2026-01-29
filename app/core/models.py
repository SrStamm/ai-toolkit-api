from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass
class TokenUsage:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


@dataclass
class CostBreakdown:
    input_cost: float
    output_cost: float
    total_cost: float
    currency: str = "USD"


@dataclass
class LLMResponse(Generic[T]):
    content: T
    usage: TokenUsage
    cost: CostBreakdown
    model: str
    provider: str
