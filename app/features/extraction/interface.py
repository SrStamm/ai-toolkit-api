from abc import ABC, abstractmethod


class SourceInterface(ABC):
    @abstractmethod
    async def extract(self, url: str) -> str:
        pass


class CleanerInterface(ABC):
    @abstractmethod
    def clean(self, raw_content: str) -> str:
        pass
