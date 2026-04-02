"""
Facade principal para el pipeline RAG.

Coordina IngestionService y QueryService.
"""

from collections.abc import AsyncIterator
from uuid import UUID

from fastapi import UploadFile

from app.api.rag.ingestion_service import IngestionService
from app.api.rag.query_service import QueryService
from app.api.rag.reranker import Reranker
from app.api.rag.metrics_collector import MetricsCollector
from app.api.rag.schemas import QueryResponse
from app.infrastructure.storage.interfaces import VectorStoreInterface
from app.infrastructure.storage.hybrid_ai import HybridEmbeddingService
from app.application.llm.client import LLMClient


class RAGService:
    """
    Facade que coordina los servicios de ingestión y query.
    """

    def __init__(
        self,
        llm_client: LLMClient,
        vector_store: VectorStoreInterface,
        embed_service: HybridEmbeddingService,
    ) -> None:
        self.vector_store = vector_store
        self.embed_service = embed_service

        # Initialize components
        self.metrics = MetricsCollector()
        self.reranker = Reranker(vector_store)

        # Initialize services
        self.ingestion = IngestionService(
            vector_store=vector_store,
            embed_service=embed_service,
        )
        self.query = QueryService(
            llm_client=llm_client,
            vector_store=vector_store,
            embed_service=embed_service,
            reranker=self.reranker,
            metrics=self.metrics,
        )

    # ===========================================================================
    # Ingestion Methods (delegated to IngestionService)
    # ===========================================================================

    async def ingest_pdf_file(
        self,
        file: UploadFile,
        source: str,
        domain: str,
        topic: str,
        progress_callback=None,
    ):
        """Synchronous PDF ingestion."""
        return await self.ingestion.ingest_pdf_file(
            file=file,
            source=source,
            domain=domain,
            topic=topic,
            progress_callback=progress_callback,
        )

    async def ingest_pdf_file_stream(
        self, file: UploadFile, source: str, domain: str, topic: str
    ) -> AsyncIterator[dict]:
        """Streaming PDF ingestion."""
        async for progress in self.ingestion.ingest_pdf_file_stream(
            file=file,
            source=source,
            domain=domain,
            topic=topic,
        ):
            yield progress

    async def ingest_document(
        self,
        url: str,
        source: str,
        domain: str,
        topic: str,
        progress_callback=None,
    ):
        """Synchronous URL ingestion."""
        return await self.ingestion.ingest_document(
            url=url,
            source=source,
            domain=domain,
            topic=topic,
            progress_callback=progress_callback,
        )

    async def ingest_document_stream(
        self, url: str, source: str, domain: str, topic: str
    ) -> AsyncIterator[dict]:
        """Streaming URL ingestion."""
        async for progress in self.ingestion.ingest_document_stream(
            url=url,
            source=source,
            domain=domain,
            topic=topic,
        ):
            yield progress

    # ===========================================================================
    # Query Methods (delegated to QueryService)
    # ===========================================================================

    def ask(
        self,
        session_id: UUID,
        user_question: str,
        domain: str | None = None,
        topic: str | None = None,
    ) -> QueryResponse:
        """Synchronous RAG query."""
        return self.query.ask(
            session_id=session_id,
            user_question=user_question,
            domain=domain,
            topic=topic,
        )

    async def chat_stream(
        self,
        session_id: UUID,
        user_question: str,
        domain: str | None = None,
        topic: str | None = None,
    ) -> AsyncIterator[str]:
        """Streaming RAG query."""
        async for chunk in self.query.chat_stream(
            session_id=session_id,
            user_question=user_question,
            domain=domain,
            topic=topic,
        ):
            yield chunk


def create_rag_service(
    llm_client: LLMClient,
    vector_store: VectorStoreInterface,
    embed_service: HybridEmbeddingService,
) -> RAGService:
    """Factory function for RAGService."""
    return RAGService(
        llm_client=llm_client,
        vector_store=vector_store,
        embed_service=embed_service,
    )
