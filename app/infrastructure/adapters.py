from llama_index.core.embeddings import BaseEmbedding
from pydantic import Field 
from .storage.hybrid_ai import HybridEmbeddingService

class LlamaIndexHybridAdapter(BaseEmbedding):
    # Usamos Field para que Pydantic (que usa LlamaIndex) no se queje
    service: HybridEmbeddingService = Field(exclude=True)

    def __init__(self, hybrid_service: HybridEmbeddingService, **kwargs):
        super().__init__(service=hybrid_service, **kwargs)

    def _get_query_embedding(self, query: str) -> list[float]:
        # Usamos tu lógica manual de query
        result = self.service.embed(query, query=True)
        return result.dense

    def _get_text_embedding(self, text: str) -> list[float]:
        # Usamos tu lógica manual de pasaje
        result = self.service.embed(text, query=False)
        return result.dense

    async def _aget_query_embedding(self, query: str) -> list[float]:
        return self._get_query_embedding(query)
