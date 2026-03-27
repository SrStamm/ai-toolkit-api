# Subida a Qdrant con LlamaIndex

from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.core import StorageContext
from qdrant_client import QdrantClient
from ...infrastructure.storage.hybrid_ai import get_hybrid_embeddign_service

_hybrid_service = get_hybrid_embeddign_service()

def sparse_doc_fn(texts: list[str]):
    results = _hybrid_service.batch_embed(texts)
    indices = [list(r.sparse["indices"]) for r in results]
    values = [list(r.sparse["values"]) for r in results]
    return indices, values

def sparse_query_fn(query):
    query_str = query.query_str if hasattr(query, "query_str") else str(query)

    result = _hybrid_service.embed(query_str)

    return [result.sparse["indices"]], [result.sparse["values"]]

class LlamaIndexer:
    def __init__(self, host="qdrant", port=6333, collection="documents_llama"):
        self.client = QdrantClient(host=host, port=port)

        self.vectore_store = QdrantVectorStore(
            client=self.client,
            collection_name=collection,
            enable_hybrid=True,
            sparse_doc_fn=sparse_doc_fn,
            sparse_query_fn=sparse_query_fn,
        )

        self.storage_context = StorageContext.from_defaults(
            vector_store=self.vectore_store
        )

    def get_storage_context(self):
        return self.storage_context
