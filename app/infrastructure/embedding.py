from sentence_transformers import CrossEncoder
import torch

torch.set_num_threads(1)
torch.set_num_interop_threads(1)

_rerank_model = None

def get_rerank_model():
    global _rerank_model
    if _rerank_model is None:
        _rerank_model = CrossEncoder(
            "cross-encoder/ms-marco-MiniLM-L-4-v2", device="cpu"
        )
    return _rerank_model
