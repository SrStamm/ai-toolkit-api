"""
RAG Service - Main entry point.

This module re-exports from the new modular structure for backwards compatibility.
New code should import directly from the submodules.
"""

from app.api.rag.rag_service import RAGService, create_rag_service
from app.api.rag.ingestion_service import IngestionService
from app.api.rag.query_service import QueryService
from app.api.rag.reranker import Reranker
from app.api.rag.metrics_collector import MetricsCollector


# For backwards compatibility
def get_rag_service() -> RAGService:
    """Get RAG service instance. Deprecated - use factory function instead."""
    from app.api.rag.rag_service import create_rag_service
    from app.infrastructure.storage.qdrant_client import get_qdrant_store
    from app.infrastructure.storage.hybrid_ai import get_hybrid_embeddign_service
    from app.application.llm.client import get_llm_client

    return create_rag_service(
        llm_client=get_llm_client(),
        vector_store=get_qdrant_store(),
        embed_service=get_hybrid_embeddign_service(),
    )


# Re-export schemas for convenience
from app.api.rag.schemas import (
    Citation,
    LLMAnswer,
    Metadata,
    QueryResponse,
)
