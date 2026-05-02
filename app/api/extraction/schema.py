from pydantic import BaseModel

class ChunkWithMetadata(BaseModel):
    text: str
    section: str | None = None
