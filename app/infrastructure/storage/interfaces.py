from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, List, Dict
from pydantic import BaseModel


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
    def create_point(self, hash_id, vector, payload) -> Any:
        pass

    @abstractmethod
    def insert_vector(self, points: List[Any]) -> None:
        """Insert or update vectors"""
        pass

    @abstractmethod
    def retrieve(self, hash_ids: List[Any]) -> List[Any]:
        """Retrieve vectors by their IDs"""
        pass

    @abstractmethod
    def rerank(self, query: str, search_result: list) -> List[Any]:
        """Sort order results"""
        pass

    @abstractmethod
    def delete_old_data(self, source: str) -> None:
        pass


class EmbeddingInterface(ABC):
    @abstractmethod
    def embed(self, text: str, query: bool = False) -> List[Any]:
        pass

    @abstractmethod
    def batch_embed(self, chunk_list: list[str], query: bool = False) -> List[Any]:
        pass


class HybridVector(BaseModel):
    dense: List[float]
    sparse: Dict[str, Any]

class HybridEmbeddingInterface(ABC):
    @abstractmethod
    def embed(self, text: str, query: bool = False) -> HybridVector:
        pass

    @abstractmethod
    def batch_embed(self, chunk_list: list[str], query: bool = False) -> List[HybridVector]:
        pass

