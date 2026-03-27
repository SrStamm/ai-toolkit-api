from llama_index.core import Settings
from ...infrastructure.storage.hybrid_ai import get_hybrid_embeddign_service
from ...infrastructure.adapters import LlamaIndexHybridAdapter

def setup_llamaindex():
    # Obtain manual service
    my_hybrid_service = get_hybrid_embeddign_service()

    # wrap with adapter
    adapter = LlamaIndexHybridAdapter(hybrid_service=my_hybrid_service)

    # its assigned to llama_index
    Settings.embed_model = adapter
