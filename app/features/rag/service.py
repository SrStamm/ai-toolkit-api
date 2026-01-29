from typing import Optional
from fastapi import Depends
import json
import structlog
from app.features.extraction.exceptions import EmptySourceContentError, SourceException
from app.features.extraction.factory import SourceFactory
from .exceptions import ChunkingError
from .providers.local_ai import EmbeddignService, get_embeddign_service
from .interfaces import FilterContext, VectorStoreInterface
from .providers import qdrant_client
from .prompt import PROMPT_TEMPLATE
from app.core.llm_client import LLMClient, get_llm_client


class RAGService:
    def __init__(
        self,
        llm_client: LLMClient,
        vector_store: VectorStoreInterface,
        embed_service: EmbeddignService,
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

        points = []
        for i, chunk in enumerate(chunks):
            payload = {
                "text": chunk,
                "source": source,
                "domain": domain.lower(),
                "topic": topic.lower(),
                "chunk_index": i,
            }

            vector = self.embed_service.embed(chunk)
            point = self.vector_store.create_point(vector, payload)
            points.append(point)

        self.vector_store.insert_vector(points)

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

    def ask(self, user_question: str, domain: str, topic: str):
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

        prompt = PROMPT_TEMPLATE.format(context=context, question=user_question)

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

        return {
            "answer": parsed["answer"],
            "citations": citations,
            "metadata": {
                "tokens": response.usage.total_tokens,
                "cost": response.cost.total_cost,
            },
        }


def get_rag_service(
    llm_client: LLMClient = Depends(get_llm_client),
    vector_store: VectorStoreInterface = Depends(qdrant_client.get_qdrant_store),
    embed_service: EmbeddignService = Depends(get_embeddign_service),
):
    return RAGService(llm_client, vector_store, embed_service)
