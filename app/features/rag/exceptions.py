class ChunkingError(Exception):
    def __init__(self, msg: str):
        super().__init__(f"Chunking error: {msg}")
        self.msg = msg


class EmbeddingError(Exception):
    pass


class VectorStoreError(Exception):
    pass
