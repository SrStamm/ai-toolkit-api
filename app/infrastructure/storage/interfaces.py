from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, List, Dict
from pydantic import BaseModel


@dataclass
class FilterContext:
    domain: str | None = None
    topic: str | None = None

class HybridVector(BaseModel):
    dense: List[float]
    sparse: Dict[str, Any]

class VectorStoreInterface(ABC):
    @abstractmethod
    def query(
        self, query_vector: HybridVector, limit: int, filter_context: FilterContext
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
    def delete_old_data(self, source: str, timestamp: int) -> None:
        """Delete old chunks for a specific source (legacy/compatibility)."""
        pass

    @abstractmethod
    def delete_by_filter(self, filter_conditions: Dict[str, Any]) -> None:
        """Delete points matching a generic set of filter conditions."""
        pass

    @abstractmethod
    def list_sources(self, domain: str | None = None) -> List[Dict[str, Any]]:
        """List unique sources with metadata using scroll (for document management)."""
        pass

    @abstractmethod
    def get_source_metadata(self, source: str) -> Dict[str, Any] | None:
        """Get aggregated metadata for a specific source (domain, topic, chunks count)."""
        pass


class EmbeddingInterface(ABC):
    @abstractmethod
    def embed(self, text: str, query: bool = False) -> List[Any]:
        pass

    @abstractmethod
    def batch_embed(self, chunk_list: list[str], query: bool = False) -> List[Any]:
        pass



class HybridEmbeddingInterface(ABC):
    @abstractmethod
    def embed(self, text: str, query: bool = False) -> HybridVector:
        pass

    @abstractmethod
    def batch_embed(self, chunk_list: list[str], query: bool = False) -> List[HybridVector]:
        pass

