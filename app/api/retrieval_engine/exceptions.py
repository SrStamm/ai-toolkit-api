import json


class ChunkingError(Exception):
    def __init__(self, msg: str):
        super().__init__(f"Chunking error: {msg}")
        self.msg = msg


class EmbeddingError(Exception):
    pass


class VectorStoreError(Exception):
    pass


def error_event(message: str, recoverable: bool):
    return f"data: {json.dumps({'type': 'error', 'message': message, 'recoverable': recoverable})}\n\n"
