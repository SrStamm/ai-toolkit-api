from typing import List
from sentence_transformers import SentenceTransformer
from ....core.custom_logging import time_response
from ..exceptions import EmbeddingError
from ..interfaces import EmbeddingInterface


class EmbeddingService(EmbeddingInterface):
    def __init__(self):
        self.embed_model = SentenceTransformer("intfloat/multilingual-e5-small")

    @time_response
    def embed(self, text: str, query: bool = False) -> List[float]:
        try:
            if query:
                embedding = self.embed_model.encode(
                    f"query: {text}", normalize_embeddings=True
                )
            else:
                embedding = self.embed_model.encode(
                    f"passage: {text}", normalize_embeddings=True
                )

            return embedding.tolist()
        except Exception as e:
            raise EmbeddingError(str(e)) from e

    @time_response
    def batch_embed(self, list: list[str], query: bool = False) -> List[List[float]]:
        try:
            batchs = [f"query: {x}" if query else f"passage: {x}" for x in list]

            embeddings = self.embed_model.encode(batchs, batch_size=len(batchs))

            return embeddings.tolist()
        except Exception as e:
            raise EmbeddingError(str(e)) from e


embedding = EmbeddingService()


def get_embeddign_service() -> EmbeddingService:
    return embedding
