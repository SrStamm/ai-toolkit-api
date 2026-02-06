from abc import ABC, abstractmethod
from typing import Optional

from fastapi import UploadFile


class SourceInterface(ABC):
    @abstractmethod
    async def extract(self, url: Optional[str], file: Optional[UploadFile]) -> str:
        pass


class CleanerInterface(ABC):
    @abstractmethod
    def clean(self, raw_content: str) -> str:
        pass

    @abstractmethod
    def chunk(self, clean_text: str) -> list[str]:
        pass
