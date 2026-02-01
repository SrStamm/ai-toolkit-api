from typing import List
import numpy as np
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
    def batch_embed(
        self, list: list[str], query: bool = False, batch_size: int = 50
    ) -> List[List[float]]:
        try:
            all_batches = []

            for start in range(0, len(list), batch_size):
                end = min(start + batch_size, len(list))

                # Slice batchs
                batchs = list[start:end]

                # Format batchs
                batch_formated = [
                    f"query: {x}" if query else f"passage: {x}" for x in batchs
                ]

                # encode batchs
                batch_result = self.embed_model.encode(
                    batch_formated, batch_size=len(batch_formated)
                )

                # extend list
                all_batches.append(batch_result)

            if len(all_batches) == 1:
                final = all_batches[0]
            else:
                final = np.concatenate(all_batches)

            return final.tolist()
        except Exception as e:
            raise EmbeddingError(str(e)) from e


embedding = EmbeddingService()


def get_embeddign_service() -> EmbeddingService:
    return embedding
