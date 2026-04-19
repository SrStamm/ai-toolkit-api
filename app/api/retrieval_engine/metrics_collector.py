"""
Abstracción para el logging de métricas del pipeline RAG.
"""

import structlog
from uuid import UUID

from app.domain.models import LLMResponse
from app.infrastructure.metrics import (
    rag_vector_search_duration_seconds,
    rag_pipeline_duration_seconds,
    rag_chunks_retrieved,
    llm_total_cost_dollars,
    llm_tokens_used_total,
)


class MetricsCollector:
    """
    Centraliza el logging de métricas del pipeline RAG.
    """

    def __init__(self) -> None:
        self.logger = structlog.get_logger()

    def log_vector_search(
        self,
        query: str,
        domain: str | None,
        topic: str | None,
        chunks_found: int,
        duration_seconds: float,
    ) -> None:
        """Log metrics for a vector search operation."""
        rag_vector_search_duration_seconds.labels(
            domain=domain or "all", topic=topic or "all"
        ).observe(duration_seconds)

        rag_chunks_retrieved.labels(
            domain=domain or "all", topic=topic or "all"
        ).observe(chunks_found)

    def log_pipeline_duration(
        self,
        operation: str,
        domain: str | None,
        topic: str | None,
        duration_seconds: float,
    ) -> None:
        """Log pipeline duration metric."""
        rag_pipeline_duration_seconds.labels(
            operation_type=operation, domain=domain or "all", topic=topic or "all"
        ).observe(duration_seconds)

    def log_llm_usage(self, response: LLMResponse, stream: bool = False) -> None:
        """Log LLM usage metrics and cost."""
        log_type = "LLM_CALL_STREAM" if stream else "LLM_CALL"

        self.logger.info(
            log_type,
            provider=response.provider,
            model=response.model,
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
            total_tokens=response.usage.total_tokens,
            input_cost=f"${response.cost.input_cost:.6f}",
            output_cost=f"${response.cost.output_cost:.6f}",
            total_cost=f"${response.cost.total_cost:.6f}",
        )

        # Cost metrics
        llm_total_cost_dollars.labels(
            provider=response.provider, model=response.model
        ).inc(response.cost.total_cost)

        # Token metrics
        llm_tokens_used_total.labels(
            provider=response.provider, model=response.model, token_type="prompt"
        ).inc(response.usage.prompt_tokens)

        llm_tokens_used_total.labels(
            provider=response.provider, model=response.model, token_type="completion"
        ).inc(response.usage.completion_tokens)

    def log_cost_tracking(
        self,
        session_id: UUID,
        total_tokens: int,
        total_cost: float,
    ) -> None:
        """Track session cost."""
        from app.domain.services.cost_tracker import cost_tracker

        cost_tracker.add(session_id, total_tokens, total_cost)
