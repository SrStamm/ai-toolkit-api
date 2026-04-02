"""
Servicio para queries y respuestas del pipeline RAG.
"""

import asyncio
import json
import time
from collections.abc import AsyncIterator
from uuid import UUID

import structlog
from pydantic import ValidationError

from app.api.rag.schemas import Citation, LLMAnswer, Metadata, QueryResponse
from app.api.rag.prompt import PROMPT_TEMPLATE, PROMPT_TEMPLATE_CHAT
from app.api.rag.reranker import Reranker
from app.api.rag.metrics_collector import MetricsCollector
from app.infrastructure.storage.interfaces import FilterContext, VectorStoreInterface
from app.infrastructure.storage.hybrid_ai import HybridEmbeddingService
from app.application.llm.client import LLMClient


class QueryService:
    """
    Responsable de las queries al vector store y generación de respuestas.
    """

    def __init__(
        self,
        llm_client: LLMClient,
        vector_store: VectorStoreInterface,
        embed_service: HybridEmbeddingService,
        reranker: Reranker,
        metrics: MetricsCollector,
    ) -> None:
        self.llm_client = llm_client
        self.vector_store = vector_store
        self.embed_service = embed_service
        self.reranker = reranker
        self.metrics = metrics
        self.logger = structlog.get_logger()

    def retrieve(self, text: str, domain: str | None, topic: str | None) -> list:
        """Retrieve relevant chunks from vector store."""
        # Generate query embedding
        vector_query = self.embed_service.embed(text, query=True)

        # Build filter context
        context = FilterContext()
        if domain:
            context.domain = domain.lower()
        if topic:
            context.topic = topic.lower()

        # Search
        start_search = time.perf_counter()
        result = self.vector_store.query(vector_query, limit=20, filter_context=context)
        duration = time.perf_counter() - start_search

        # Log metrics
        self.metrics.log_vector_search(
            query=text,
            domain=domain,
            topic=topic,
            chunks_found=len(result),
            duration_seconds=duration,
        )

        return result

    def _build_citations(self, query_result: list) -> list[Citation]:
        """Build citations from query results."""
        seen = set()
        citations: list[Citation] = []

        for hit in query_result:
            src = hit.payload["source"]
            if src not in seen:
                seen.add(src)
                citations.append(
                    Citation(
                        source=src,
                        chunk_index=hit.payload["chunk_index"],
                        text=hit.payload["text"],
                    )
                )

        return citations

    def _parse_answer(self, content: str) -> str:
        """Parse LLM answer from response."""
        try:
            parsed = LLMAnswer.model_validate_json(content)
            return parsed.answer
        except ValidationError:
            return content

    def ask(
        self,
        session_id: UUID,
        user_question: str,
        domain: str | None = None,
        topic: str | None = None,
    ) -> QueryResponse:
        """Synchronous RAG query."""
        start_pipeline = time.perf_counter()

        # Retrieve relevant chunks
        query_result = self.retrieve(user_question, domain, topic)
        self.logger.info("query_chunks_retrieved", quantity=len(query_result))

        if not query_result:
            self.logger.info(
                "no_rag_results",
                domain=domain,
                topic=topic,
                user_question=user_question,
            )
            return QueryResponse(
                answer="I don't have enough information to answer that question.",
                citations=[],
                metadata=Metadata(tokens=0, cost=0.0),
            )

        # Rerank
        rerank_result = self.reranker.rerank(user_question, query_result)
        self.logger.info("chunks_reranked", quantity=len(rerank_result))

        # Build context
        context = "\n\n".join(
            f"[{i + 1}]\n{chunk.payload['text']}"
            for i, chunk in enumerate(rerank_result)
        )

        # Generate answer
        prompt = PROMPT_TEMPLATE_CHAT.format(context=context, question=user_question)
        response = self.llm_client.generate_content(prompt)

        # Log metrics
        self.metrics.log_llm_usage(response, stream=False)
        self.metrics.log_pipeline_duration(
            operation="ask",
            domain=domain,
            topic=topic,
            duration_seconds=time.perf_counter() - start_pipeline,
        )

        # Parse answer
        answer = self._parse_answer(response.content)

        # Build citations
        citations = self._build_citations(rerank_result)

        # Track costs
        self.metrics.log_cost_tracking(
            session_id=session_id,
            total_tokens=response.usage.total_tokens,
            total_cost=response.cost.total_cost,
        )

        return QueryResponse(
            answer=answer,
            citations=citations,
            metadata=Metadata(
                tokens=response.usage.total_tokens,
                cost=response.cost.total_cost,
                model=response.model,
                provider=response.provider,
            ),
        )

    async def chat_stream(
        self,
        session_id: UUID,
        user_question: str,
        domain: str | None = None,
        topic: str | None = None,
    ) -> AsyncIterator[str]:
        """Streaming RAG query."""
        start_pipeline = time.perf_counter()

        # Retrieve
        query_result = self.retrieve(user_question, domain, topic)
        self.logger.info("query_chunks_retrieved", quantity=len(query_result))

        if not query_result:
            yield f"data: {json.dumps({'type': 'error', 'content': 'No results found'})}\n\n"
            return

        # Rerank
        rerank_result = self.reranker.rerank(user_question, query_result)
        self.logger.info("chunks_reranked", quantity=len(rerank_result))

        # Build context
        context = "\n\n".join(
            f"[{i + 1}]\n{chunk.payload['text']}"
            for i, chunk in enumerate(rerank_result)
        )

        # Generate answer (streaming)
        prompt = PROMPT_TEMPLATE.format(context=context, question=user_question)

        final_response = None
        async for chunk, response_data in self.llm_client.generate_content_stream(
            prompt
        ):
            if response_data:
                final_response = response_data
            else:
                yield f"data: {json.dumps({'type': 'content', 'content': chunk})}\n\n"
                await asyncio.sleep(0)  # Allow other tasks to run

        # Log metrics
        if final_response:
            self.metrics.log_llm_usage(final_response, stream=True)
            self.metrics.log_cost_tracking(
                session_id=session_id,
                total_tokens=final_response.usage.total_tokens,
                total_cost=final_response.cost.total_cost,
            )

        self.metrics.log_pipeline_duration(
            operation="ask_stream",
            domain=domain,
            topic=topic,
            duration_seconds=time.perf_counter() - start_pipeline,
        )

        # Send citations
        citations = self._build_citations(rerank_result)
        yield f"data: {json.dumps({'type': 'citations', 'citations': [c.model_dump() for c in citations]})}\n\n"

        # Send metadata
        if final_response:
            metadata_dict = {
                "type": "metadata",
                "tokens": final_response.usage.total_tokens,
                "cost": final_response.cost.total_cost,
                "model": final_response.model,
                "estimated": True,
            }
            yield f"data: {json.dumps(metadata_dict)}\n\n"

        yield f"data: {json.dumps({'type': 'done'})}\n\n"
