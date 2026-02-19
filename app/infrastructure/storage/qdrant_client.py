from typing import List
from qdrant_client import QdrantClient
from qdrant_client import models

from ..embedding import get_rerank_model
from ..logging import time_response
from ...api.rag.exceptions import VectorStoreError
from .interfaces import HybridVector, VectorStoreInterface
import structlog


qdrant = QdrantClient(host="qdrant", port=6333)

COLLECTION_NAME = "documents"
log = structlog.getLogger()


class QdrantStore(VectorStoreInterface):
    def __init__(self, client: QdrantClient) -> None:
        self.client = client
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
                    "dense": models.VectorParams(
                        size=384, distance=models.Distance.COSINE, on_disk=True
                    ),
                },
                sparse_vectors_config={
                    "sparse": models.SparseVectorParams(
                        index=models.SparseIndexParams(
                            on_disk=True
                        )
                    )
                },
                quantization_config=models.ScalarQuantization(
                    scalar=models.ScalarQuantizationConfig(
                        type=models.ScalarType.INT8, quantile=0.99, always_ram=False
                    )
                ),
            )

            log.info("Qdrant collection created", collection=COLLECTION_NAME)

        except Exception as e:
            raise VectorStoreError("Failed to create collection") from e

    @time_response
    def query(
        self, query_vector: HybridVector, limit: int, filter_context
    ) -> List[models.ScoredPoint]:
        conditions = []
        if filter_context.domain:
            conditions.append(
                models.FieldCondition(
                    key="domain", match=models.MatchValue(value=filter_context.domain)
                )
            )

        if filter_context.topic:
            conditions.append(
                models.FieldCondition(
                    key="topic", match=models.MatchValue(value=filter_context.topic)
                )
            )

        query_filter = models.Filter(must=conditions) if conditions else None

        search_result = self.client.query_points(
            collection_name=COLLECTION_NAME,
            prefetch=[
                models.Prefetch(query=query_vector.dense, using="dense", limit=limit),
                models.Prefetch(query=models.SparseVector(
                    indices=query_vector.sparse["indices"],
                    values=query_vector.sparse["values"]
                ), using="sparse", limit=limit)
            ],
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            with_payload=True,
            query_filter=query_filter,
        ).points

        return search_result

    def create_point(self, hash_id, vector, payload) -> models.PointStruct:
        return models.PointStruct(
            id=hash_id,
            vector=vector,
            payload=payload
        )

    @time_response
    def retrieve(self, hash_ids: List[str]) -> List[models.Record]:
        return self.client.retrieve(
            collection_name=COLLECTION_NAME,
            ids=hash_ids,
            with_payload=True,
            with_vectors=True,
        )

    @time_response
    def insert_vector(self, points: List[models.PointStruct], batch_size: int = 64):
        for i in range(0, len(points), batch_size):
            batch = points[i : i + batch_size]
            self.client.upsert(collection_name=COLLECTION_NAME, points=batch)

    @time_response
    def rerank(self, query: str, search_result: list) -> List[models.ScoredPoint]:
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
    def delete_old_data(self, source: str, timestamp: int):
        """
        Delete old chunks with specific source.
        Useful for re-ingest and keep only the most recent version
        """
        deleted = self.client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(key="source", match=models.MatchValue(value=source)),
                        models.FieldCondition(key="ingested_at", range=models.Range(lt=timestamp))
                    ]
                )
            ),
        )
        log.info("Old data cleaned", source=source, deleted_count=deleted.operation_id)


qdrant_client = QdrantStore(qdrant)


def get_qdrant_store() -> QdrantStore:
    return qdrant_client
