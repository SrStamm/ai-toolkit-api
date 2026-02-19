from typing import List
import time
import structlog
import torch
from sentence_transformers import SentenceTransformer, SparseEncoder

from ...infrastructure.logging import time_response
from ...infrastructure.metrics import embedding_duration_seconds, embedding_requests_total
from ...api.rag.exceptions import EmbeddingError
from .interfaces import HybridEmbeddingInterface, HybridVector

logger = structlog.get_logger()


def _parse_sparse_output(sparse_output) -> dict:
    """Parse sparse encoder output to dict with indices and values."""
    # Case 1: Sparse tensor (COO format) - has indices() and values() methods
    if hasattr(sparse_output, "indices") and hasattr(sparse_output, "values") and hasattr(sparse_output, "to_dense"):
        # Coalesce the tensor to ensure we can safely access indices
        sparse_coalesced = sparse_output.coalesce()
        indices = sparse_coalesced.indices()
        values = sparse_coalesced.values()
        
        # indices shape is (1, nnz) for single item, need to flatten
        indices_list = indices.tolist()
        values_list = values.tolist()
        
        # If nested (batch=1), unwrap
        if indices_list and isinstance(indices_list[0], list):
            indices_list = indices_list[0]
        if values_list and isinstance(values_list[0], list):
            values_list = values_list[0]
            
        return {
            "indices": indices_list,
            "values": values_list
        }
    
    # Case 2: Already a dict with indices/values (each being tensors)
    if isinstance(sparse_output, dict):
        if "indices" in sparse_output and "values" in sparse_output:
            indices = sparse_output["indices"]
            values = sparse_output["values"]
            
            # Convert to lists
            indices_list = indices.tolist() if hasattr(indices, "tolist") else list(indices)
            values_list = values.tolist() if hasattr(values, "tolist") else list(values)
            
            # If nested, unwrap
            if indices_list and isinstance(indices_list[0], list):
                indices_list = indices_list[0]
            if values_list and isinstance(values_list[0], list):
                values_list = values_list[0]
            
            return {
                "indices": indices_list,
                "values": values_list
            }
    
    # Case 3: Dense tensor (batch, vocab)
    if isinstance(sparse_output, torch.Tensor):
        # Convert to sparse and extract
        sparse = sparse_output.to_sparse()
        indices = sparse.indices()
        values = sparse.values()
        
        indices_list = indices.tolist()
        values_list = values.tolist()
        
        # If nested, unwrap
        if indices_list and isinstance(indices_list[0], list):
            indices_list = indices_list[0]
        if values_list and isinstance(values_list[0], list):
            values_list = values_list[0]
            
        return {
            "indices": indices_list,
            "values": values_list
        }
    
    raise EmbeddingError(f"Unknown sparse encoder output format: {type(sparse_output)}")


class HybridEmbeddingService(HybridEmbeddingInterface):
    def __init__(self, dense_model: SentenceTransformer, sparse_model: SparseEncoder):
        self.dense_model = dense_model
        self.sparse_model = sparse_model

    @time_response
    def embed(self, text: str, query: bool = False) -> HybridVector:
        start = time.perf_counter()
        model_name = self.dense_model.model_id if hasattr(self.dense_model, 'model_id') else 'default'
        
        try:
            # 1. Generate dense vector 
            text_input = f"query: {text}" if query else f"passage: {text}"
            dense_vec = self.dense_model.encode(text_input, normalize_embeddings=True)

            # 2. Generate sparse vector
            sparse_result = self.sparse_model.encode(text)
            
            # Convert sparse tensor to dict format
            sparse_dict = _parse_sparse_output(sparse_result)

            duration = time.perf_counter() - start
            embedding_duration_seconds.labels(model=model_name, batch_size='1').observe(duration)
            embedding_requests_total.labels(model=model_name, status='success').inc()

            return HybridVector(
                dense=dense_vec.tolist(),
                sparse=sparse_dict
            )

        except Exception as e:
            embedding_requests_total.labels(model=model_name, status='error').inc()
            raise EmbeddingError(str(e)) from e

    @time_response
    def batch_embed(
        self, chunk_list: list[str], query: bool = False, batch_size: int = 16
    ) -> List[HybridVector]:
        if not chunk_list:
            raise EmbeddingError("Chunk list is empty")

        start = time.perf_counter()
        model_name = self.dense_model.model_id if hasattr(self.dense_model, 'model_id') else 'default'

        final_hybrid_vectors = []

        try:
            for i in range(0, len(chunk_list), batch_size):
                batch = chunk_list[i : i + batch_size]

                # Dense
                batch_formated = [f"query: {x}" if query else f"passage: {x}" for x in batch]
                dense_results = self.dense_model.encode(batch_formated, normalize_embeddings=True)

                # Sparse - process each text individually to get consistent output
                for j in range(len(batch)):
                    sparse_single = self.sparse_model.encode(batch[j])
                    sparse_dict = _parse_sparse_output(sparse_single)
                    
                    d_vec = dense_results[j].tolist()

                    final_hybrid_vectors.append(
                        HybridVector(
                            dense=d_vec,
                            sparse=sparse_dict
                        )
                    )

            duration = time.perf_counter() - start
            embedding_duration_seconds.labels(model=model_name, batch_size=str(batch_size)).observe(duration)
            embedding_requests_total.labels(model=model_name, status='success').inc()

            return final_hybrid_vectors
        except Exception as e:
            embedding_requests_total.labels(model=model_name, status='error').inc()
            raise EmbeddingError(str(e)) from e


embedding = HybridEmbeddingService(
    dense_model=SentenceTransformer(
            "sentence-transformers/all-MiniLM-L6-v2", device="cpu"
        ),
    sparse_model=SparseEncoder("prithivida/Splade_PP_en_v2")
    )


def get_hybrid_embeddign_service() -> HybridEmbeddingService:
    return embedding
