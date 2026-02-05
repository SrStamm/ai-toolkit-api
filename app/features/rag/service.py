import asyncio
from datetime import datetime, UTC
from typing import Optional
import hashlib
from uuid import UUID, uuid5, NAMESPACE_DNS
from fastapi import Depends
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

    def _prepare_ingestion_points(self, chunks, source, topic, domain):
        # Retrieve points if exists
        hash_ids = set()

        # Hash ids
        hash_ids = [
            hashlib.sha256((chunk + source).encode()).hexdigest() for chunk in chunks
        ]

        # Convert ids to strings
        hash_ids_deterministic = [
            str(uuid5(NAMESPACE_DNS, hash_id)) for hash_id in hash_ids
        ]

        # call vector store to check existing chunks
        chunks_in_db = self.vector_store.retrieve(hash_ids_deterministic)

        # Get a set of chunk ids existed
        ids_in_db = [chunk.id for chunk in chunks_in_db]

        # Filter chunks to process
        chunks_to_embed = [
            (hash_ids_deterministic[i], chunk, i)
            for i, chunk in enumerate(chunks)
            if hash_ids_deterministic[i] not in ids_in_db
        ]

        points_to_upsert = []
        timestamp = datetime.now(UTC).isoformat()

        # --- Case A: new chunks ----
        if chunks_to_embed:
            # Get texts to process and embed
            texts_to_process = [item[1] for item in chunks_to_embed]
            new_vectors = self.embed_service.batch_embed(texts_to_process)

            if len(new_vectors) != len(texts_to_process):
                raise EmbeddingError(
                    f"Vector count mismatch: expected {len(texts_to_process)}, got {len(new_vectors)}"
                )

            # Create points and add to upsert list
            for (h_id, text, original_idx), vector in zip(chunks_to_embed, new_vectors):
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

        # --- Case B: upsert all existing chunks ----
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

        return points_to_upsert, chunks_to_embed, chunks_in_db, timestamp

    async def ingest_document(self, url, source, domain, topic):
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

        # Clean content
        content = cleaner.clean(raw_data)

        if not content.strip():
            raise EmptySourceContentError(url)

        # Chunks content
        chunks = cleaner.chunk(content)

        if not chunks:
            raise ChunkingError("No chunks generated")

        # call function to prepare points
        points_to_upsert, chunks_to_embed, chunks_in_db, ingestion_timestamp = (
            self._prepare_ingestion_points(chunks, source, topic, domain)
        )

        # Insert points on vector database
        if points_to_upsert:
            self.vector_store.insert_vector(points_to_upsert)
            self.logger.info(
                "ingest_completed",
                url=url,
                source=source,
                domain=domain,
                topic=topic,
                chunks_processed=len(points_to_upsert),
                new=len(chunks_to_embed),
                updated=len(chunks_in_db),
            )

        if chunks_in_db:
            self.vector_store.delete_old_data(
                source=source, timestamp=ingestion_timestamp
            )

    async def ingest_document_stream(self, url, source, domain, topic):
        """Generator which broadcast progress events"""

        # Extracting
        yield {"progress": 10, "step": "Extracting content from URL"}
        extractor, cleaner = SourceFactory.get_extractor_and_cleaner(url)

        try:
            raw_data = await extractor.extract(url)
        except SourceException as e:
            self.logger.warning(
                "Source extraction failed", error=str(e), url=url, source=source
            )
            raise

        # Cleaning
        yield {"progress": 30, "step": "Cleaning and processing content"}
        content = cleaner.clean(raw_data)

        if not content.strip():
            raise EmptySourceContentError(url)

        chunks = cleaner.chunk(content)

        if not chunks:
            raise ChunkingError("No chunks generated")

        # Retrieve points if exists
        hashes = [
            hashlib.sha256((chunk + source).encode()).hexdigest() for chunk in chunks
        ]

        all_uuid_ids = [str(uuid5(NAMESPACE_DNS, h)) for h in hashes]

        chunks_in_db = self.vector_store.retrieve(all_uuid_ids)
        ids_in_db = [chunk.id for chunk in chunks_in_db]

        # Separate
        news = [
            (all_uuid_ids[i], c, i)
            for i, c in enumerate(chunks)
            if all_uuid_ids[i] not in ids_in_db
        ]

        yield {
            "progress": 50,
            "step": f"Analysis complete: {len(news)} new chunks, {len(chunks_in_db)} existing.",
        }

        timestamp = datetime.now(UTC).isoformat()
        points_to_upsert = []

        if news:
            yield {"progress": 60, "step": "Generating embeddings for new content..."}

            # Run a function in a separate thread
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
                    f"Vector count mismatch: expected {len(texts_to_process)}, got {len(vectors)}"
                )

            # Creating points
            yield {"progress": 80, "step": "Creating vector points"}

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

        if chunks_in_db:
            yield {
                "progress": 85,
                "step": "Updating timestamps for existing content...",
            }

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

            self.vector_store.delete_old_data(source=source, timestamp=timestamp)

        # Inserting
        if points_to_upsert:
            yield {"progress": 95, "step": "Storing in vector database"}
            self.vector_store.insert_vector(points_to_upsert)

            self.logger.info(
                "ingest_completed",
                url=url,
                source=source,
                domain=domain,
                topic=topic,
                chunks_processed=len(points_to_upsert),
                new=len(news),
                updated=len(chunks_in_db),
            )

        yield {"progress": 100, "step": "Done!", "chunks_processed": len(chunks)}

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


def get_rag_service(
    llm_client: LLMClient = Depends(get_llm_client),
    vector_store: VectorStoreInterface = Depends(qdrant_client.get_qdrant_store),
    embed_service: EmbeddingService = Depends(get_embeddign_service),
):
    return RAGService(llm_client, vector_store, embed_service)
