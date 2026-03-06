# Subida a Qdrant con LlamaIndex

from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.core import StorageContext
from qdrant_client import QdrantClient
from fastembed import SparseTextEmbedding

_sparse_model = SparseTextEmbedding(model_name="prithivida/Splade_PP_en_v1")

def sparse_doc_fn(texts: list[str]):
    embeddings = list(_sparse_model.embed(texts))
    indices = [list(e.indices) for e in embeddings]
    values = [list(e.values) for e in embeddings]
    return indices, values

def sparse_query_fn(query):
    query_str = query.query_str if hasattr(query, "query_str") else str(query)
    embedding = list(_sparse_model.embed([query_str]))[0]

    return [embedding.indices.tolist()], [embedding.values.tolist()]

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
