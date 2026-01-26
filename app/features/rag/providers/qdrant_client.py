from typing import List
from uuid import uuid4
from sentence_transformers import CrossEncoder
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    MatchValue,
    PointStruct,
    ScoredPoint,
    VectorParams,
    Filter,
)
from app.core.custom_logging import time_response
from app.features.rag.exceptions import VectorStoreError
from ..interfaces import VectorStoreInterface
import structlog


qdrant = QdrantClient(host="qdrant", port=6333)

COLLECTION_NAME = "documents"
log = structlog.getLogger()


class QdrantStore(VectorStoreInterface):
    def __init__(self, client: QdrantClient) -> None:
        self.client = client
        self.rerank_model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

    @time_response
    def create_collection(self):
        log.info("Verifying if Qdrant collection exists", collection=COLLECTION_NAME)

        exists = self.client.collection_exists(COLLECTION_NAME)

        if exists:
            log.info("Qdrant collection exists", collection=COLLECTION_NAME)
            return

        try:
            self.client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=384, distance=Distance.COSINE),
            )

            log.info("Qdrant collection created", collection=COLLECTION_NAME)

        except Exception as e:
            raise VectorStoreError("Failed to create collection") from e

    @time_response
    def query(
        self, query_vector: list[float], limit: int, filter_context
    ) -> List[ScoredPoint]:
        search_result = self.client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            with_payload=True,
            limit=limit,
            query_filter=Filter(
                must=[
                    FieldCondition(
                        key="domain", match=MatchValue(value=filter_context.domain)
                    ),
                    FieldCondition(
                        key="topic", match=MatchValue(value=filter_context.topic)
                    ),
                ]
            ),
        ).points

        return search_result

    @time_response
    def create_point(self, vector, payload) -> PointStruct:
        return PointStruct(id=str(uuid4()), vector=vector, payload=payload)

    @time_response
    def insert_vector(self, points: List[PointStruct], batch_size: int = 64):
        for i in range(0, len(points), batch_size):
            batch = points[i : i + batch_size]
            self.client.upsert(collection_name=COLLECTION_NAME, points=batch)

    @time_response
    def rerank(self, query: str, search_result: list) -> List[ScoredPoint]:
        # create pairs (question, text of chunk)
        pairs = [[query, hit.payload["text"]] for hit in search_result]

        # model give us a relevant points for each pair
        scores = self.rerank_model.predict(pairs)

        # match the score with your result
        for i, hit in enumerate(search_result):
            hit.payload["rerank_score"] = scores[i]

        # sort from highest to lowest according to the new score
        search_result.sort(key=lambda x: x.score, reverse=True)

        return search_result[:3]


qdrant_client = QdrantStore(qdrant)


def get_qdrant_store() -> QdrantStore:
    return qdrant_client
