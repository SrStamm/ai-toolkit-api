from typing import List
import time
import numpy as np
import structlog

from ....infrastructure.embedding import get_embedding_model
from ....infrastructure.logging import time_response
from ....infrastructure.metrics import embedding_duration_seconds, embedding_requests_total
from ..exceptions import EmbeddingError
from ..interfaces import EmbeddingInterface

logger = structlog.get_logger()


class EmbeddingService(EmbeddingInterface):
    def __init__(self):
        # self.embed_model = SentenceTransformer("intfloat/multilingual-e5-small")
        # self.embed_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        self.embed_model = get_embedding_model()

    @time_response
    def embed(self, text: str, query: bool = False) -> List[float]:
        start = time.perf_counter()
        model_name = self.embed_model.model_id if hasattr(self.embed_model, 'model_id') else 'default'
        
        try:
            if query:
                embedding = self.embed_model.encode(
                    f"query: {text}", normalize_embeddings=True
                )
            else:
                embedding = self.embed_model.encode(
                    f"passage: {text}", normalize_embeddings=True
                )

            duration = time.perf_counter() - start
            embedding_duration_seconds.labels(model=model_name, batch_size='1').observe(duration)
            embedding_requests_total.labels(model=model_name, status='success').inc()
            
            return embedding.tolist()
        except Exception as e:
            embedding_requests_total.labels(model=model_name, status='error').inc()
            raise EmbeddingError(str(e)) from e

    @time_response
    def batch_embed(
        self, chunk_list: list[str], query: bool = False, batch_size: int = 16
    ) -> List[List[float]]:
        if len(chunk_list) == 0:
            raise EmbeddingError("Chunk list is empty")

        start = time.perf_counter()
        model_name = self.embed_model.model_id if hasattr(self.embed_model, 'model_id') else 'default'

        try:
            all_batches = []

            for batch_enum, start_idx in enumerate(range(0, len(chunk_list), batch_size)):
                end = min(start_idx + batch_size, len(chunk_list))

                logger.debug(f"Proccessing batch {batch_enum + 1}: {start_idx} to {end}")

                # Slice batchs
                batchs = chunk_list[start_idx:end]

                # Format batchs
                batch_formated = [
                    f"query: {x}" if query else f"passage: {x}" for x in batchs
                ]

                # encode batchs
                try:
                    batch_result = self.embed_model.encode(
                        batch_formated, batch_size=len(batch_formated)
                    )
                except (RuntimeError, ValueError, MemoryError) as e:
                    raise EmbeddingError(f"Encoding failed: {str(e)}")

                # extend list
                all_batches.append(batch_result)

            if len(all_batches) == 1:
                final = all_batches[0]
            else:
                final = np.concatenate(all_batches)

            if any(np.isnan(v).any() or np.isinf(v).any() for v in final):
                raise EmbeddingError("One or more vectors contain NaN or Inf values")

            duration = time.perf_counter() - start
            embedding_duration_seconds.labels(model=model_name, batch_size=str(batch_size)).observe(duration)
            embedding_requests_total.labels(model=model_name, status='success').inc()
            
            return final.tolist()
        except Exception as e:
            embedding_requests_total.labels(model=model_name, status='error').inc()
            raise EmbeddingError(str(e)) from e


embedding = EmbeddingService()


def get_embeddign_service() -> EmbeddingService:
    return embedding
