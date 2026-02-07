import asyncio
from datetime import datetime, UTC
from typing import AsyncIterator, Optional
import hashlib
from uuid import UUID, uuid5, NAMESPACE_DNS
from fastapi import Depends, UploadFile
import json
import structlog
from pydantic import ValidationError

from .schemas import LLMAnswer, Metadata, QueryResponse
from .exceptions import ChunkingError, EmbeddingError
from .providers.local_ai import EmbeddingService, get_embeddign_service
from .interfaces import FilterContext, VectorStoreInterface
from .providers import qdrant_client
from .prompt import PROMPT_TEMPLATE, PROMPT_TEMPLATE_CHAT
from ..extraction.exceptions import EmptySourceContentError, SourceException
from ..extraction.factory import SourceFactory
from ...core.llm_client import LLMClient, get_llm_client
from ...core.cost_tracker import cost_tracker


class RAGService:
    def __init__(
        self,
        llm_client: LLMClient,
        vector_store: VectorStoreInterface,
        embed_service: EmbeddingService,
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
        if progress_callback:
            await progress_callback(50, "Analyzing chunks...")

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

        if progress_callback:
            await progress_callback(
                55, f"Found {len(news)} new, {len(chunks_in_db)} existing chunks"
            )

        timestamp = datetime.now(UTC).isoformat()
        points_to_upsert = []

        # Process new chunks
        if news:
            if progress_callback:
                await progress_callback(60, "Generating embeddings...")

            # Timeout calculation
            estimated_time = len(chunks) * 0.5
            timeout = max(60, estimated_time * 2)

            try:
                texts_to_process = [item[1] for item in news]
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

            if progress_callback:
                await progress_callback(80, "Creating vector points...")

            # Create points
            for (h_id, text, original_idx), vector in zip(news, vectors):
                point = self.vector_store.create_point(
                    hash_id=h_id,
                    vector=vector,
                    payload={
                        "text": text,
                        "source": source,
                        "domain": domain.lower(),
                        "topic": topic.lower(),
                        "chunk_index": original_idx,
                        "ingested_at": timestamp,
                    },
                )
                points_to_upsert.append(point)

        # Update existing chunks
        if chunks_in_db:
            if progress_callback:
                await progress_callback(85, "Updating existing chunks...")

            for chunk_db in chunks_in_db:
                point = self.vector_store.create_point(
                    hash_id=chunk_db.id,
                    vector=chunk_db.vector,
                    payload={
                        **chunk_db.payload,
                        "ingested_at": timestamp,
                    },
                )
                points_to_upsert.append(point)

        # Insert into vector store
        if points_to_upsert:
            if progress_callback:
                await progress_callback(95, "Storing in vector database...")

            self.vector_store.insert_vector(points_to_upsert)

        # Clean old data
        if chunks_in_db:
            self.vector_store.delete_old_data(source=source, timestamp=timestamp)

        return {
            "chunks_processed": len(points_to_upsert),
            "new": len(news),
            "updated": len(chunks_in_db),
        }

    # ================================
    # PUBLIC METHODS - PDF Ingestion
    # ================================

    async def ingest_pdf_file(
        self, file: UploadFile, source: str, domain: str, topic: str
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
        result = await self._process_ingestion(chunks, source, topic, domain)

        self.logger.info(
            "pdf_ingest_completed",
            filename=file.filename,
            source=source,
            domain=domain,
            topic=topic,
            **result,
        )

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

        result = await self._process_ingestion(chunks, source, domain, topic)

        yield {"progress": 95, "step": "Finalizing..."}

        self.logger.info(
            "pdf_ingest_completed",
            filename=file.filename,
            source=source,
            domain=domain,
            topic=topic,
            **result,
        )

        yield {"progress": 100, "step": "Done!", **result}

    # ================================
    # PUBLIC METHODS - URL Ingestion
    # ================================

    async def ingest_document(self, url, source, domain, topic):
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
        result = await self._process_ingestion(chunks, source, topic, domain)

        self.logger.info(
            "ingest_completed",
            url=url,
            source=source,
            domain=domain,
            topic=topic,
            **result,
        )

    async def ingest_document_stream(
        self, url: str, source: str, domain: str, topic: str
    ) -> AsyncIterator[dict]:
        """Streaming ingestion from URL with progress reporting"""

        async def report_progress(progress: int, step: str):
            yield {"progress": progress, "step": step}

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
            chunks, source, domain, topic, progress_callback=None
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

        yield {"progress": 100, "step": "Done!", **result}

    def query(self, text, domain: Optional[str], topic: Optional[str]):
        # Get vector for text
        vector_query = self.embed_service.embed(text, True)

        # Create filter context
        context = FilterContext()

        if domain:
            context.domain = domain.lower()
        if topic:
            context.topic = topic.lower()

        # Search in DB using vector
        return self.vector_store.query(vector_query, limit=10, filter_context=context)

    def ask(
        self,
        session_id: UUID,
        user_question: str,
        domain: Optional[str] = None,
        topic: Optional[str] = None,
    ):
        query_result = self.query(user_question, domain, topic)

        if not query_result:
            self.logger.info(
                "NO RAG results",
                domain=domain,
                topic=topic,
                user_question=user_question,
            )

        rerank_result = self.vector_store.rerank(user_question, query_result)

        context = "\n\n".join(
            f"[{i + 1}]\n{chunk.payload['text']}"
            for i, chunk in enumerate(rerank_result)
        )

        prompt = PROMPT_TEMPLATE_CHAT.format(context=context, question=user_question)

        response = self.llm_client.generate_content(prompt)

        try:
            parsed = LLMAnswer.model_validate_json(response.content)
            answer = parsed.answer
        except ValidationError:
            answer = response.content

        seen = set()
        citations = []

        for q in query_result:
            src = q.payload["source"]
            if src in seen:
                continue
            seen.add(src)

            citations.append(
                {
                    "source": src,
                    "chunk_index": q.payload["chunk_index"],
                }
            )

        self.logger.info(
            "LLM_CALL",
            provider=response.provider,
            model=response.model,
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
            total_tokens=response.usage.total_tokens,
            input_cost=f"${response.cost.input_cost:.6f}",
            output_cost=f"${response.cost.output_cost:.6f}",
            total_cost=f"${response.cost.total_cost:.6f}",
        )

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
    ):
        query_result = self.query(user_question, domain, topic)

        if not query_result:
            yield f"data: {json.dumps({'type': 'error', 'content': 'No results found'})}\n\n"
            return

        rerank_result = self.vector_store.rerank(user_question, query_result)

        context = "\n\n".join(
            f"[{i + 1}]\n{chunk.payload['text']}"
            for i, chunk in enumerate(rerank_result)
        )

        prompt = PROMPT_TEMPLATE.format(context=context, question=user_question)

        # LLM Stream response
        final_response = None
        async for chunk, response_data in self.llm_client.generate_content_stream(
            prompt
        ):
            if response_data:
                final_response = response_data
            else:
                yield f"data: {json.dumps({'type': 'content', 'content': chunk})}\n\n"
                await asyncio.sleep(0)

        # Costs logs
        if final_response:
            self.logger.info(
                "LLM_CALL_STREAM",
                provider=final_response.provider,
                model=final_response.model,
                prompt_tokens=final_response.usage.prompt_tokens,
                completion_tokens=final_response.usage.completion_tokens,
                total_tokens=final_response.usage.total_tokens,
                input_cost=f"${final_response.cost.input_cost:.6f}",
                output_cost=f"${final_response.cost.output_cost:.6f}",
                total_cost=f"${final_response.cost.total_cost:.6f}",
            )

        # Send citations
        seen = set()
        citations = []
        for q in query_result:
            src = q.payload["source"]
            if src not in seen:
                seen.add(src)
                citations.append(
                    {"source": src, "chunk_index": q.payload["chunk_index"]}
                )

        yield f"data: {json.dumps({'type': 'citations', 'citations': citations})}\n\n"

        # Send final metadata
        if final_response:
            yield f"data: {json.dumps({'type': 'metadata', 'tokens': final_response.usage.total_tokens, 'cost': final_response.cost.total_cost, 'model': final_response.model, 'estimated': True})}\n\n"

            cost_tracker.add(
                session_id,
                final_response.usage.total_tokens,
                final_response.cost.total_cost,
            )

        yield f"data: {json.dumps({'type': 'done'})}\n\n"


def get_rag_service(
    llm_client: LLMClient = Depends(get_llm_client),
    vector_store: VectorStoreInterface = Depends(qdrant_client.get_qdrant_store),
    embed_service: EmbeddingService = Depends(get_embeddign_service),
):
    return RAGService(llm_client, vector_store, embed_service)
