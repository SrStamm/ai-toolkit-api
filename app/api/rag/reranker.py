"""
Abstracción para el reranking de resultados de búsqueda.
"""

from typing import Protocol

from app.infrastructure.storage.interfaces import VectorStoreInterface


class RerankerInterface(Protocol):
    """Protocol for reranker implementations."""

    def rerank(self, query: str, results: list) -> list:
        """Rerank search results based on query relevance."""
        ...


class Reranker:
    """
    Reranker que usa el modelo de cross-encoder para reordenar resultados.
    """

    def __init__(self, vector_store: VectorStoreInterface) -> None:
        self.vector_store = vector_store

    def rerank(self, query: str, results: list) -> list:
        """Rerank results using the configured model."""
        if not results:
            return []

        return self.vector_store.rerank(query, results)
