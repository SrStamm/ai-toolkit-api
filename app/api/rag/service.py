import asyncio
from datetime import datetime, UTC
import time
from typing import AsyncIterator, Optional
import hashlib
from uuid import UUID, uuid5, NAMESPACE_DNS
from fastapi import UploadFile
import json
import structlog
from pydantic import ValidationError

from .schemas import LLMAnswer, Metadata, QueryResponse
from ...infrastructure.storage.qdrant_client import get_qdrant_store
from ...infrastructure.storage.interfaces import FilterContext, VectorStoreInterface
from ...infrastructure.storage.hybrid_ai import HybridEmbeddingService, get_hybrid_embeddign_service
from .exceptions import ChunkingError, EmbeddingError
from .prompt import PROMPT_TEMPLATE, PROMPT_TEMPLATE_CHAT
from ..extraction.exceptions import EmptySourceContentError, SourceException
from ..extraction.factory import SourceFactory
from ...application.llm.client import LLMClient, get_llm_client
from ...domain.services.cost_tracker import cost_tracker
from ...infrastructure.metrics import (
    rag_vector_search_duration_seconds, 
    rag_pipeline_duration_seconds, 
    rag_chunks_retrieved,
    embedding_duration_seconds,
    embedding_requests_total,
    documents_ingested_total,
    documents_chunks_total,
    llm_total_cost_dollars,
    llm_tokens_used_total,
)



class RAGService:
    def __init__(
        self,
        llm_client: LLMClient,
        vector_store: VectorStoreInterface,
        embed_service: HybridEmbeddingService,
    ):
        self.llm_client = llm_client
        self.vector_store = vector_store
        self.embed_service = embed_service
        self.logger = structlog.get_logger()

    def _generate_deterministic_ids(self, chunks: list[str], source: str) -> list[str]:
        """Generate deterministic UUIDs for chunks"""
        hash_ids = set()

        hash_ids = [
            hashlib.sha256((chunk + source).encode()).hexdigest() for chunk in chunks
        ]

        return [str(uuid5(NAMESPACE_DNS, hash_id)) for hash_id in hash_ids]

    async def _process_ingestion(
        self,
        chunks: list[str],
        source: str,
        domain: str,
        topic: str,
        progress_callback: Optional[callable] = None,
    ):
        """
        Process ingestion with optional progress reporting.
        This eliminates ALL duplication between sync/stream and URL/PDF variants.
        """

        async def report(percent, msg):
            if progress_callback:
                await progress_callback(percent, msg)

        await report(50, "Analyzing chunks...")

        # Generate IDs
        hash_ids = self._generate_deterministic_ids(chunks, source)

        # Check existing
        chunks_in_db = self.vector_store.retrieve(hash_ids)
        ids_in_db = {chunk.id for chunk in chunks_in_db}

        # Separate new vs existing
        news = [
            (hash_ids[i], c, i)
            for i, c in enumerate(chunks)
            if hash_ids[i] not in ids_in_db
        ]

        await report(55, f"Found {len(news)} new, {len(chunks_in_db)} existing chunks")

        timestamp = int(datetime.now(UTC).timestamp())
        old_points_to_upsert = []

        # Clean old data
        if chunks_in_db:
            self.vector_store.delete_old_data(source=source, timestamp=timestamp)

        # Process new chunks
        if news:
            await report(60, "Generating embeddings...")

            # Timeout calculation
            estimated_time = len(news) * 0.5
            timeout = max(60, estimated_time * 2)

            BATCH_SIZE = 20

            for i in range(0, len(news), BATCH_SIZE):
                try:
                    batch = news[i:i+BATCH_SIZE]
                    texts_to_process = [item[1] for item in batch]
                    vectors = await asyncio.wait_for(
                        asyncio.to_thread(self.embed_service.batch_embed, texts_to_process),
                        timeout=timeout,
                    )

                except asyncio.TimeoutError:
                    timeout_minutes = timeout / 60
                    raise EmbeddingError(
                        f"Embedding timed out after {timeout_minutes:.1f} minutes"
                    )

                if len(vectors) != len(texts_to_process):
                    raise EmbeddingError(
                            f"Vector mismatch: expected {len(texts_to_process)}, got {len(vectors)}"
                        )

                new_points = []

                # Create points
                for (h_id, text, original_idx), vector in zip(batch, vectors):
                    point = self.vector_store.create_point(
                        hash_id=h_id,
                        vector={
                            "dense": vector.dense,
                            "sparse": vector.sparse
                        },
                        payload={
                            "text": text,
                            "source": source,
                            "domain": domain.lower(),
                            "topic": topic.lower(),
                            "chunk_index": original_idx,
                            "ingested_at": timestamp,
                        },
                    )
                    new_points.append(point)

                self.vector_store.insert_vector(new_points)

                await report(60, f"Ingested batch {i} of {len(news) + BATCH_SIZE}...")

        # Update existing chunks
        if chunks_in_db:
            await report(85, "Updating existing chunks...")

            for chunk_db in chunks_in_db:
                point = self.vector_store.create_point(
                    hash_id=chunk_db.id,
                    vector=chunk_db.vector,
                    payload={
                        **chunk_db.payload,
                        "ingested_at": timestamp,
                    },
                )
                old_points_to_upsert.append(point)

        # Insert into vector store
        if old_points_to_upsert:
            await report(95, "Storing in vector database...")

            self.vector_store.insert_vector(old_points_to_upsert)

        return {
            "chunks_processed": len(chunks),
            "new": len(news),
            "updated": len(chunks_in_db),
        }

    # ================================
    # PUBLIC METHODS - PDF Ingestion
    # ================================

    async def ingest_pdf_file(
        self, file: UploadFile, source: str, domain: str, topic: str, progress_callback=None
    ):
        """Synchronous PDF ingestion"""
        extractor, cleaner = SourceFactory.get_pdf_cleaner()

        # Extract
        raw_data = await extractor.extract(file)

        # Clean and Chunk
        content = cleaner.clean(raw_data)
        if not content.strip():
            raise EmptySourceContentError(file.filename)

        chunks = cleaner.chunk(content)
        if not chunks:
            raise ChunkingError("No chunks generated")

        # Process
        result = await self._process_ingestion(chunks=chunks, source=source, domain=domain, topic=topic, progress_callback=progress_callback)

        # Log and metrics
        self.logger.info(
            "pdf_ingest_completed",
            filename=file.filename,
            source=source,
            domain=domain,
            topic=topic,
            **result,
        )
        
        documents_ingested_total.labels(source_type='pdf', status='success').inc()
        documents_chunks_total.labels(source_type='pdf').inc(result['chunks_processed'])

    async def ingest_pdf_file_stream(
        self, file: UploadFile, source: str, domain: str, topic: str
    ):
        """Streaming PDF ingestion with progress reporting"""

        # Extraction
        yield {"progress": 10, "step": "Extracting text from PDF"}

        extractor, cleaner = SourceFactory.get_pdf_cleaner()

        try:
            raw_data = await extractor.extract(file)
        except Exception as e:
            self.logger.error(
                "PDF extraction failed", error=str(e), filename=file.filename
            )
            raise

        # Cleaning
        yield {"progress": 30, "step": "Cleaning and processing PDF content"}

        content = cleaner.clean(raw_data)
        if not content.strip():
            raise EmptySourceContentError(file.filename)

        chunks = cleaner.chunk(content)
        if not chunks:
            raise ChunkingError("No chunks generated")

        # Process with progress reporting
        yield {"progress": 50, "step": "Processing chunks..."}

        result = await self._process_ingestion(chunks=chunks, source=source, domain=domain, topic=topic, progress_callback=None)

        yield {"progress": 95, "step": "Finalizing..."}

        self.logger.info(
            "pdf_ingest_completed",
            filename=file.filename,
            source=source,
            domain=domain,
            topic=topic,
            **result,
        )
        
        documents_ingested_total.labels(source_type='pdf', status='success').inc()
        documents_chunks_total.labels(source_type='pdf').inc(result['chunks_processed'])

        yield {"progress": 100, "step": "Done!", **result}

    # ================================
    # PUBLIC METHODS - URL Ingestion
    # ================================

    async def ingest_document(
        self, url: str, source: str, domain: str, topic: str, progress_callback: Optional[callable] =None
    ):
        """Synchronous ingestion from URL"""
        # Get tools since factory
        extractor, cleaner = SourceFactory.get_extractor_and_cleaner(url)

        # Extract crude content
        try:
            raw_data = await extractor.extract(url)
        except SourceException as e:
            self.logger.warning(
                "Source extraction failed", error=str(e), url=url, source=source
            )
            raise

        # Clean and chunk
        content = cleaner.clean(raw_data)
        if not content.strip():
            raise EmptySourceContentError(url)

        chunks = cleaner.chunk(content)
        if not chunks:
            raise ChunkingError("No chunks generated")

        # Process (no progress callback)
        result = await self._process_ingestion(
            chunks=chunks, source=source, domain=domain, topic=topic, progress_callback=progress_callback
        )

        self.logger.info(
            "ingest_completed",
            url=url,
            source=source,
            domain=domain,
            topic=topic,
            **result,
        )
        
        documents_ingested_total.labels(source_type='url', status='success').inc()
        documents_chunks_total.labels(source_type='url').inc(result['chunks_processed'])

    async def ingest_document_stream(
        self, url: str, source: str, domain: str, topic: str
    ) -> AsyncIterator[dict]:
        """Streaming ingestion from URL with progress reporting"""

        # Extraction
        yield {"progress": 10, "step": "Extracting content from URL"}

        extractor, cleaner = SourceFactory.get_extractor_and_cleaner(url)
        try:
            raw_data = await extractor.extract(url)
        except SourceException as e:
            self.logger.warning("Source extraction failed", error=str(e), url=url)
            raise

        # Cleaning
        yield {"progress": 30, "step": "Cleaning and processing content"}

        content = cleaner.clean(raw_data)
        if not content.strip():
            raise EmptySourceContentError(url)

        chunks = cleaner.chunk(content)
        if not chunks:
            raise ChunkingError("No chunks generated")

        yield {"progress": 50, "step": "Analyzing chunks..."}

        result = await self._process_ingestion(
            chunks=chunks,
            source=source,
            domain=domain,
            topic=topic,
            progress_callback=None,
        )

        yield {"progress": 95, "step": "Finalizing..."}

        self.logger.info(
            "ingest_completed",
            url=url,
            source=source,
            domain=domain,
            topic=topic,
            **result,
        )
        
        documents_ingested_total.labels(source_type='url', status='success').inc()
        documents_chunks_total.labels(source_type='url').inc(result['chunks_processed'])

        yield {"progress": 100, "step": "Done!", **result}

    # ============================================================================
    # PUBLIC METHODS - Query and Chat
    # ============================================================================

    def query(self, text, domain: Optional[str], topic: Optional[str]):
        """Retrieve relevant chunks from vector store"""
        # Generate query embedding
        vector_query = self.embed_service.embed(text, True)

        # Build filter context
        context = FilterContext()
        if domain:
            context.domain = domain.lower()
        if topic:
            context.topic = topic.lower()

        # Search
        start_search = time.perf_counter()

        result = self.vector_store.query(vector_query, limit=20, filter_context=context)

        finish_search = time.perf_counter() - start_search
        rag_vector_search_duration_seconds.labels(
            domain=domain or 'all',
            topic=topic or 'all'
        ).observe(finish_search)

        rag_chunks_retrieved.labels(
            domain=domain or 'all',
            topic=topic or 'all'
        ).observe(len(result))

        return result

    def _build_citations(self, query_result: list) -> list[dict]:
        """Centralized LLM usage logging"""
        seen = set()
        citations = []

        for hit in query_result:
            src = hit.payload["source"]
            if src not in seen:
                seen.add(src)
                citations.append(
                    {
                        "source": src,
                        "chunk_index": hit.payload["chunk_index"],
                    }
                )

        return citations

    def _log_llm_usage(self, response, stream: bool = False):
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

    def ask(
        self,
        session_id: UUID,
        user_question: str,
        domain: Optional[str] = None,
        topic: Optional[str] = None,
    ) -> QueryResponse:
        """Synchronous RAG query"""
        start_pipeline = time.perf_counter()

        # Retrieve relevant chunks
        query_result = self.query(user_question, domain, topic)

        if not query_result:
            self.logger.info(
                "no_rag_results",
                domain=domain,
                topic=topic,
                user_question=user_question,
            )
            # ✅ Return early with empty response
            return QueryResponse(
                answer="I don't have enough information to answer that question.",
                citations=[],
                metadata=Metadata(tokens=0, cost=0.0),
            )

        # Rerank
        rerank_result = self.vector_store.rerank(user_question, query_result)


        # Build context
        context = "\n\n".join(
            f"[{i + 1}]\n{chunk.payload['text']}"
            for i, chunk in enumerate(rerank_result)
        )

        # Generate answer
        prompt = PROMPT_TEMPLATE_CHAT.format(context=context, question=user_question)
        response = self.llm_client.generate_content(prompt)

        finish_pipeline = time.perf_counter() - start_pipeline
        rag_pipeline_duration_seconds.labels(
            operation_type='ask',
            domain=domain or 'all',
            topic=topic or 'all'
        ).observe(finish_pipeline)

        # Log cost metrics
        llm_total_cost_dollars.labels(
            provider=response.provider,
            model=response.model
        ).inc(response.cost.total_cost)

        llm_tokens_used_total.labels(
            provider=response.provider,
            model=response.model,
            token_type='prompt'
        ).inc(response.usage.prompt_tokens)

        llm_tokens_used_total.labels(
            provider=response.provider,
            model=response.model,
            token_type='completion'
        ).inc(response.usage.completion_tokens)

        # Parse answer
        try:
            parsed = LLMAnswer.model_validate_json(response.content)
            answer = parsed.answer
        except ValidationError:
            answer = response.content

        # Build citations
        citations = self._build_citations(query_result)

        # Log usage
        self._log_llm_usage(response, stream=False)

        # Track costs
        cost_tracker.add(
            session_id, response.usage.total_tokens, response.cost.total_cost
        )

        return QueryResponse(
            answer=answer,
            citations=citations,
            metadata=Metadata(
                tokens=response.usage.total_tokens,
                cost=response.cost.total_cost,
            ),
        )

    async def chat_stream(
        self,
        session_id: UUID,
        user_question: str,
        domain: Optional[str] = None,
        topic: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """Streaming RAG query"""
        start_pipeline = time.perf_counter()

        # Retrieve
        query_result = self.query(user_question, domain, topic)

        if not query_result:
            yield f"data: {json.dumps({'type': 'error', 'content': 'No results found'})}\n\n"
            return

        # Rerank
        rerank_result = self.vector_store.rerank(user_question, query_result)


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
                await asyncio.sleep(0)  # ✅ Allow other tasks to run

        # Log usage and cost metrics
        if final_response:
            self._log_llm_usage(final_response, stream=True)
            
            llm_total_cost_dollars.labels(
                provider=final_response.provider,
                model=final_response.model
            ).inc(final_response.cost.total_cost)

            llm_tokens_used_total.labels(
                provider=final_response.provider,
                model=final_response.model,
                token_type='prompt'
            ).inc(final_response.usage.prompt_tokens)

            llm_tokens_used_total.labels(
                provider=final_response.provider,
                model=final_response.model,
                token_type='completion'
            ).inc(final_response.usage.completion_tokens)

        finish_pipeline = time.perf_counter() - start_pipeline
        rag_pipeline_duration_seconds.labels(
            operation_type='ask_stream',
            domain=domain or 'all',
            topic=topic or 'all'
        ).observe(finish_pipeline)

        # Send citations
        citations = self._build_citations(query_result)
        yield f"data: {json.dumps({'type': 'citations', 'citations': citations})}\n\n"

        # Send metadata
        if final_response:
            yield f"data: {
                json.dumps(
                    {
                        'type': 'metadata',
                        'tokens': final_response.usage.total_tokens,
                        'cost': final_response.cost.total_cost,
                        'model': final_response.model,
                        'estimated': True,
                    }
                )
            }\n\n"

            cost_tracker.add(
                session_id,
                final_response.usage.total_tokens,
                final_response.cost.total_cost,
            )

        yield f"data: {json.dumps({'type': 'done'})}\n\n"


def create_rag_service() -> RAGService:
    return RAGService(
        llm_client=get_llm_client(),
        vector_store=get_qdrant_store(),
        embed_service=get_hybrid_embeddign_service(),
    )


def get_rag_service() -> RAGService:
    return create_rag_service()
