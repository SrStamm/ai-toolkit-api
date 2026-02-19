from typing import List
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    MatchValue,
    PointStruct,
    ScalarQuantization,
    ScalarType,
    ScoredPoint,
    SparseIndexParams,
    SparseVector,
    VectorParams,
    SparseVectorParams,
    Filter,
    FilterSelector,
    Record,
    DatetimeRange,
    ScalarQuantizationConfig,
)

from ..embedding import get_rerank_model
from ..logging import time_response
from ...api.rag.exceptions import VectorStoreError
from .interfaces import VectorStoreInterface
import structlog


qdrant = QdrantClient(host="qdrant", port=6333)

COLLECTION_NAME = "documents"
log = structlog.getLogger()


class QdrantStore(VectorStoreInterface):
    def __init__(self, client: QdrantClient) -> None:
        self.client = client
        # self.rerank_model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
        # self.rerank_model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L4-v2")
        self.rerank_model = get_rerank_model()

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
                vectors_config={
                    "dense": VectorParams(
                        size=384, distance=Distance.COSINE, on_disk=True
                    ),
                },
                sparse_vectors_config={
                    "sparse": SparseVectorParams(
                        index=SparseIndexParams(
                            on_disk=True
                        )
                    )
                },
                quantization_config=ScalarQuantization(
                    scalar=ScalarQuantizationConfig(
                        type=ScalarType.INT8, quantile=0.99, always_ram=False
                    )
                ),
            )

            log.info("Qdrant collection created", collection=COLLECTION_NAME)

        except Exception as e:
            raise VectorStoreError("Failed to create collection") from e

    @time_response
    def query(
        self, query_vector: list[float], limit: int, filter_context
    ) -> List[ScoredPoint]:
        conditions = []
        if filter_context.domain:
            conditions.append(
                FieldCondition(
                    key="domain", match=MatchValue(value=filter_context.domain)
                )
            )

        if filter_context.topic:
            conditions.append(
                FieldCondition(
                    key="topic", match=MatchValue(value=filter_context.topic)
                )
            )

        query_filter = Filter(must=conditions) if conditions else None

        search_result = self.client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            with_payload=True,
            limit=limit,
            query_filter=query_filter,
        ).points

        return search_result

    def create_point(self, hash_id, vector, payload) -> PointStruct:
        return PointStruct(
            id=hash_id,
            vector=vector,
            payload=payload
        )

    @time_response
    def retrieve(self, hash_ids: List[str]) -> List[Record]:
        return self.client.retrieve(
            collection_name=COLLECTION_NAME,
            ids=hash_ids,
            with_payload=True,
            with_vectors=True,
        )

    @time_response
    def insert_vector(self, points: List[PointStruct], batch_size: int = 64):
        if points:
            print(f"DEBUG VECTOR ESTRUCTURA: {points[0].vector}")

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
            hit.payload["score"] = scores[i]

        # sort from highest to lowest according to the new score
        search_result.sort(key=lambda x: x.score, reverse=True)

        return search_result[:3]

    @time_response
    def delete_old_data(self, source):
        """
        Delete old chunks with specific source.
        Useful for re-ingest and keep only the most recent version
        """
        deleted = self.client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=FilterSelector(
                filter=Filter(
                    must=[
                        FieldCondition(key="source", match=MatchValue(value=source)),
                    ]
                )
            ),
        )
        log.info("Old data cleaned", source=source, deleted_count=deleted.operation_id)


qdrant_client = QdrantStore(qdrant)


def get_qdrant_store() -> QdrantStore:
    return qdrant_client
