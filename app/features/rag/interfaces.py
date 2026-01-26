from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, List


@dataclass
class FilterContext:
    domain: str | None = None
    topic: str | None = None


class VectorStoreInterface(ABC):
    @abstractmethod
    def query(
        self, query_vector: List[float], limit: int, filter_context: FilterContext
    ) -> list[Any]:
        """Search similar vectors"""
        pass

    @abstractmethod
    def create_point(self, vector, payload) -> Any:
        pass

    @abstractmethod
    def insert_vector(self, points: List[Any]) -> None:
        """Insert or update vectors"""
        pass

    @abstractmethod
    def rerank(self, query: str, search_result: list) -> List[Any]:
        """Sort order results"""
        pass


class EmbeddingInterface(ABC):
    @abstractmethod
    def embed(self, text: str, query: bool = False) -> List[Any]:
        pass
