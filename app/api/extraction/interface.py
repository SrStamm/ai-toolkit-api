from abc import ABC, abstractmethod
from fastapi import UploadFile
from .schema import ChunkWithMetadata


class SourceInterface(ABC):
    @abstractmethod
    async def extract(self, url: str | None, file: UploadFile | None) -> str: ...


class CleanerInterface(ABC):
    @abstractmethod
    def clean(self, raw_content: str) -> str: ...

    @abstractmethod
    def chunk(self, clean_text: str) -> list[ChunkWithMetadata]: ...
