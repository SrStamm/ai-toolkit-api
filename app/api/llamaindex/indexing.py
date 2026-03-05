# Subida a Qdrant con LlamaIndex


from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.core import StorageContext
from qdrant_client import QdrantClient


class LlamaIndexer:
    def __init__(self, host="qdrant", port=6333, collection="documents_llama"):
        self.client = QdrantClient(host=host, port=port)

        self.vectore_store = QdrantVectorStore(
            client=self.client,
            collection_name=collection,
        )

        self.storage_context = StorageContext.from_defaults(
            vector_store=self.vectore_store
        )

    def get_storage_context(self):
        return self.storage_context
