import json
from typing import Optional
from llama_index.core import VectorStoreIndex
from llama_index.core.postprocessor import SentenceTransformerRerank
from llama_index.core.vector_stores.types import MetadataFilter, MetadataFilters

from .ingestion import LlamaIngester
from .indexing import LlamaIndexer
from .config import setup_llamaindex
from ..rag.prompt import PROMPT_TEMPLATE_CHAT
from ..rag.schemas import Citation, Metadata, QueryResponse
from ...application.llm.client import LLMClient, get_llm_client

setup_llamaindex()

class LlamaIndexOrchestrator:
    def __init__(self):
        self.indexer = LlamaIndexer()
        self.ingester = LlamaIngester()
        self.index = VectorStoreIndex.from_vector_store(
            vector_store=self.indexer.vectore_store,
        )
        self.rerank = SentenceTransformerRerank(
            model="cross-encoder/mmarco-mMiniLMv2-L12-H384-v1",
            top_n=4
        )
        self.llm_client: LLMClient = get_llm_client()

    def _update_index(self):
        self.index = VectorStoreIndex.from_vector_store(
            vector_store=self.indexer.vectore_store,
        )

    def _query_filters(self, domain: Optional[str], topic: Optional[str]) -> Optional[MetadataFilters]:
        filters = []

        if domain:
            filters.append(
                MetadataFilter(key="domain", value=domain)
            )

        if topic:
            filters.append(
                MetadataFilter(key="topic", value=topic)
            )

        return MetadataFilters(filters=filters) if filters else None


    def proccess_pdf(self, pdf_path: str, source: str, domain: str, topic: str):
        storage_context = self.indexer.get_storage_context()
        response = self.ingester.ingest_pdf(
            pdf_path=pdf_path,
            source=source,
            domain=domain,
            topic=topic,
            storage_context=storage_context
        )

        self._update_index()

        return response

    def proccess_html(
        self,
        url: str,
        domain: str,
        topic: str
    ):
        storage_context = self.indexer.get_storage_context()

        response = self.ingester.ingest_html(
            url=url,
            domain=domain,
            topic=topic,
            storage_context=storage_context
        )

        self._update_index()

        return response

    def query(self, query: str):
        query_engine = self.index.as_query_engine(
            similarity_top_k=10,
            vector_store_query_mode="hybrid",
            node_postprocessors=[self.rerank]
        )

        return query_engine.query(query)

    def custom_query(self, query: str, domain: Optional[str], topic: Optional[str]) -> QueryResponse:
        query_filters = self._query_filters(domain, topic)

        # 1. Retrieval + Rerank
        retriever = self.index.as_retriever(
            similarity_top_k=8,
            vector_store_query_mode="hybrid",
            filters=query_filters
        )
        nodes = retriever.retrieve(query)
        nodes = self.rerank.postprocess_nodes(nodes, query_str=query)

        # 2. Create Context and call LLM
        context_str = "\n\n".join([n.get_content() for n in nodes])
        prompt = PROMPT_TEMPLATE_CHAT.format(context=context_str, question=query)

        # Use chat to get response with metadata
        llm_res = self.llm_client.generate_content(prompt)

        # 3. Map citations
        citations = []
        for i, node in enumerate(nodes):
            citations.append(
                Citation(
                    source=node.metadata.get("filename", "unknown"),
                    chunk_index=i,
                    text=node.get_content()
                )
            )

        # 4. Extract Metadata
        metadata = Metadata(
            tokens=llm_res.usage.total_tokens,
            cost=llm_res.cost.total_cost, 
            model=llm_res.model,
            provider=llm_res.provider
        )

        # 5. Format final response
        try:
            clean_res = llm_res.content.replace("```json", "").replace("```", "").strip()
            answer_content = json.loads(clean_res).get("answer", llm_res.content)
        except:
            answer_content = llm_res.content

        return QueryResponse(
            answer=answer_content,
            citations=citations,
            metadata=metadata
        )



_orchestrator_instance = None

def get_orchestrator():
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = LlamaIndexOrchestrator()
    return _orchestrator_instance
