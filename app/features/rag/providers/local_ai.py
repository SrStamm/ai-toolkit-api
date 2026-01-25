from typing import List
from sentence_transformers import SentenceTransformer
from app.core.custom_logging import time_response
from app.features.rag.interfaces import EmbeddingInterface


class EmbeddignService(EmbeddingInterface):
    def __init__(self):
        self.embed_model = SentenceTransformer("intfloat/multilingual-e5-small")

    @time_response
    def embed(self, text: str, query: bool = False) -> List[float]:
        if query:
            embedding = self.embed_model.encode(
                f"query: {text}", normalize_embeddings=True
            )
        else:
            embedding = self.embed_model.encode(
                f"passage: {text}", normalize_embeddings=True
            )

        return embedding.tolist()


embedding = EmbeddignService()


def get_embeddign_service() -> EmbeddignService:
    return embedding
