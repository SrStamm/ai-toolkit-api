# app/core/models.py
from sentence_transformers import SentenceTransformer, CrossEncoder
import torch

torch.set_num_threads(1)
torch.set_num_interop_threads(1)

_embedding_model = None
_rerank_model = None


def get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer(
            "sentence-transformers/all-MiniLM-L6-v2", device="cpu"
        )
        _embedding_model.half()
    return _embedding_model


def get_rerank_model():
    global _rerank_model
    if _rerank_model is None:
        _rerank_model = CrossEncoder(
            "cross-encoder/ms-marco-MiniLM-L4-v2", device="cpu"
        )
        _rerank_model.half()
    return _rerank_model
