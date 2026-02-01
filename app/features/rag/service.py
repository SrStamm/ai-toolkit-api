import asyncio
from typing import Optional
from fastapi import Depends
import json
import structlog

from .schemas import Metadata, QueryResponse
from .exceptions import ChunkingError
from .providers.local_ai import EmbeddingService, get_embeddign_service
from .interfaces import FilterContext, VectorStoreInterface
from .providers import qdrant_client
from .prompt import PROMPT_TEMPLATE, PROMPT_TEMPLATE_CHAT
from ...core.llm_client import LLMClient, get_llm_client
from ..extraction.exceptions import EmptySourceContentError, SourceException
from ..extraction.factory import SourceFactory


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

    async def ingest_document(self, url, source, domain, topic):
        # 1. Get tools since factory
        extractor, cleaner = SourceFactory.get_extractor_and_cleaner(url)

        # 2. Extract crude content
        try:
            raw_data = await extractor.extract(url)
        except SourceException as e:
            self.logger.warning(
                "Source extraction failed", error=str(e), url=url, source=source
            )
            raise

        # 3. Clean content
        content = cleaner.clean(raw_data)

        if not content.strip():
            raise EmptySourceContentError(url)

        # 4. Chunks content
        chunks = cleaner.chunk(content)

        if not chunks:
            raise ChunkingError("No chunks generated")

        # 5. Create a list of vectors
        vectors = self.embed_service.batch_embed(chunks)

        # 6. Create a list of points
        points = [
            self.vector_store.create_point(
                vector,
                {
                    "text": chunk,
                    "source": source,
                    "domain": domain.lower(),
                    "topic": topic.lower(),
                    "chunk_index": i,
                },
            )
            for i, (chunk, vector) in enumerate(zip(chunks, vectors))
        ]

        # 7. Insert points on vector database
        self.vector_store.insert_vector(points)

    async def ingest_document_stream(self, url, source, domain, topic):
        """Generator which broadcast progress events"""

        # 1. Extracting
        yield {"progress": 10, "step": "Extracting content from URL"}
        extractor, cleaner = SourceFactory.get_extractor_and_cleaner(url)

        try:
            raw_data = await extractor.extract(url)
        except SourceException as e:
            self.logger.warning(
                "Source extraction failed", error=str(e), url=url, source=source
            )
            raise

        # 2. Cleaning
        yield {"progress": 30, "step": "Cleaning and processing content"}
        content = cleaner.clean(raw_data)

        if not content.strip():
            raise EmptySourceContentError(url)

        chunks = cleaner.chunk(content)

        if not chunks:
            raise ChunkingError("No chunks generated")

        # 3. Embedding
        yield {
            "progress": 50,
            "step": f"Generating embeddings for {len(chunks)} chunks",
        }

        # Run a function in a separate thread
        vectors = await asyncio.to_thread(self.embed_service.batch_embed, chunks)

        # 4. Creating points
        yield {"progress": 80, "step": "Creating vector points"}
        points = [
            self.vector_store.create_point(
                vector,
                {
                    "text": chunk,
                    "source": source,
                    "domain": domain.lower(),
                    "topic": topic.lower(),
                    "chunk_index": i,
                },
            )
            for i, (chunk, vector) in enumerate(zip(chunks, vectors))
        ]

        # 5. Inserting
        yield {"progress": 90, "step": "Storing in vector database"}
        self.vector_store.insert_vector(points)

        # 6. Done
        yield {"progress": 100, "step": "Completed", "chunks_processed": len(chunks)}

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
            parsed = json.loads(response.content)
        except json.JSONDecodeError:
            parsed = {"answer": response.content}

        seen = set()
        citations = []
        for q in query_result:
            src = q.payload["source"]
            if src in seen:
                continue
            seen.add(src)

            citations.append({"source": src, "chunk_index": q.payload["chunk_index"]})

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

        return QueryResponse(
            answer=parsed["answer"],
            citations=citations,
            metadata=Metadata(
                tokens=response.usage.total_tokens,
                cost=response.cost.total_cost,
            ),
        )

    async def chat_stream(
        self,
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

        yield f"data: {json.dumps({'type': 'done'})}\n\n"


def get_rag_service(
    llm_client: LLMClient = Depends(get_llm_client),
    vector_store: VectorStoreInterface = Depends(qdrant_client.get_qdrant_store),
    embed_service: EmbeddingService = Depends(get_embeddign_service),
):
    return RAGService(llm_client, vector_store, embed_service)
