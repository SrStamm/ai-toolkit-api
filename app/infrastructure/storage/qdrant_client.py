from typing import List
from qdrant_client import QdrantClient
from qdrant_client import models
import torch

from app.infrastructure.embedding import get_rerank_model
from app.infrastructure.logging import time_response
from app.api.retrieval_engine.exceptions import VectorStoreError
from .interfaces import HybridVector, VectorStoreInterface
from app.core.settings import get_settings
import structlog


COLLECTION_NAME = "documents"
log = structlog.getLogger()

# Singleton client - lazily initialized
_qdrant_client: QdrantClient | None = None


def get_qdrant_client() -> QdrantClient:
    """Get or create Qdrant client using centralized settings."""
    global _qdrant_client
    if _qdrant_client is None:
        settings = get_settings()
        _qdrant_client = QdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
        )
    return _qdrant_client


class QdrantStore(VectorStoreInterface):
    def __init__(
        self, client: QdrantClient | None = None, rerank_threshold: float = 0.6
    ) -> None:
        self.client = client or get_qdrant_client()
        self.rerank_model = get_rerank_model()
        self.rerank_threshold = rerank_threshold

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
                        index=models.SparseIndexParams(on_disk=True)
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
                models.Prefetch(
                    query=models.NearestQuery(
                        nearest=query_vector.dense,
                        mmr=models.Mmr(diversity=0.5, candidates_limit=limit * 2),
                    ),
                    using="dense",
                    limit=limit,
                ),
                models.Prefetch(
                    query=models.SparseVector(
                        indices=query_vector.sparse["indices"],
                        values=query_vector.sparse["values"],
                    ),
                    using="sparse",
                    limit=limit,
                ),
            ],
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            with_payload=True,
            query_filter=query_filter,
            limit=limit,
        ).points

        return search_result

    def create_point(self, hash_id, vector, payload) -> models.PointStruct:
        return models.PointStruct(id=hash_id, vector=vector, payload=payload)

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
        if not search_result:
            return []

        pairs = [[query, hit.payload["text"]] for hit in search_result]
        scores = self.rerank_model.predict(pairs)

        scores = torch.sigmoid(torch.tensor(scores)).numpy()

        for i, hit in enumerate(search_result):
            hit.payload["rerank_score"] = float(scores[i])

        search_result.sort(key=lambda x: x.payload["rerank_score"], reverse=True)

        filtered = [
            hit
            for hit in search_result
            if hit.payload["rerank_score"] > self.rerank_threshold
        ]

        if not filtered and len(search_result) > 0:
            log.warning(
                "no_chunks_passed_rerank_threshold",
                threshold=self.rerank_threshold,
                total_chunks=len(search_result),
            )
            filtered = [search_result[0]]

        seen_texts = set()
        unique_filtered = []

        for hit in filtered:
            text_content = hit.payload["text"].strip()
            if text_content not in seen_texts:
                unique_filtered.append(hit)
                seen_texts.add(text_content)

        top_context = unique_filtered[:5]

        return top_context

    @time_response
    def delete_old_data(self, source: str, timestamp: int):
        """
        Delete old chunks with specific source.
        Useful for re-ingest and keep only the most recent version.
        Delegates to delete_by_filter for consistency.
        """
        conditions = {
            "source": source,
            "ingested_at_lt": timestamp  # Custom key to handle range
        }
        # We keep the old logic here to avoid breaking changes, 
        # but ideally, we refactor this to use delete_by_filter
        deleted = self.client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="source", match=models.MatchValue(value=source)
                        ),
                        models.FieldCondition(
                            key="ingested_at", range=models.Range(lt=timestamp)
                        ),
                    ]
                )
            ),
        )
        log.info("Old data cleaned", source=source, deleted_count=deleted.operation_id)

    @time_response
    def delete_by_filter(self, filter_conditions: dict) -> None:
        """
        Delete points matching a generic set of filter conditions.
        
        Args:
            filter_conditions: Dict with field names and values.
                            Use "field_lt", "field_gt" for range queries.
                            Example: {"source": "url", "domain": "python"}
        """
        must_conditions = []
        
        for key, value in filter_conditions.items():
            if key.endswith("_lt"):
                field = key[:-3]
                must_conditions.append(
                    models.FieldCondition(key=field, range=models.Range(lt=value))
                )
            elif key.endswith("_gt"):
                field = key[:-3]
                must_conditions.append(
                    models.FieldCondition(key=field, range=models.Range(gt=value))
                )
            else:
                must_conditions.append(
                    models.FieldCondition(key=key, match=models.MatchValue(value=value))
                )
        
        if not must_conditions:
            log.warning("delete_by_filter called with empty conditions, skipping")
            return
            
        self.client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=models.FilterSelector(
                filter=models.Filter(must=must_conditions)
            ),
        )
        log.info("Deleted points by filter", conditions=filter_conditions)

    @time_response
    def list_sources(self, domain: str | None = None) -> list[dict]:
        """
        List unique sources with chunk counts.
        Uses scroll API to iterate through points (since Qdrant doesn't have DISTINCT).
        
        Returns:
            [{"source": "...", "domain": "...", "topic": "...", "chunk_count": N}, ...]
        """
        sources_map = {}  # source -> {domain, topic, count}
        
        # Build filter for domain if provided
        scroll_filter = None
        if domain:
            scroll_filter = models.Filter(
                must=[
                    models.FieldCondition(
                        key="domain", match=models.MatchValue(value=domain)
                    )
                ]
            )
        
        # Scroll through all points
        offset = None
        while True:
            points, offset = self.client.scroll(
                collection_name=COLLECTION_NAME,
                scroll_filter=scroll_filter,
                limit=256,
                with_payload=True,
                with_vectors=False,
            )
            
            for point in points:
                payload = point.payload
                source = payload.get("source")
                if not source:
                    continue
                    
                if source not in sources_map:
                    sources_map[source] = {
                        "source": source,
                        "domain": payload.get("domain", "unknown"),
                        "topic": payload.get("topic", "unknown"),
                        "chunk_count": 0,
                    }
                sources_map[source]["chunk_count"] += 1
            
            if offset is None:
                break
                
        return list(sources_map.values())

    @time_response
    def get_source_metadata(self, source: str) -> dict | None:
        """
        Get aggregated metadata for a specific source.
        
        Returns:
            {"source": "...", "domain": "...", "topic": "...", 
             "chunk_count": N, "last_ingested": timestamp} or None
        """
        # Query points with this source
        points, _ = self.client.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="source", match=models.MatchValue(value=source)
                    )
                ]
            ),
            limit=1000,  # Assuming a source won't have more than 1000 chunks
            with_payload=True,
            with_vectors=False,
        )
        
        if not points:
            return None
            
        # Aggregate metadata
        domains = set()
        topics = set()
        max_timestamp = 0
        
        for point in points:
            payload = point.payload
            if "domain" in payload:
                domains.add(payload["domain"])
            if "topic" in payload:
                topics.add(payload["topic"])
            if "ingested_at" in payload:
                max_timestamp = max(max_timestamp, payload["ingested_at"])
        
        return {
            "source": source,
            "domain": next(iter(domains), "unknown"),
            "topic": next(iter(topics), "unknown"),
            "chunk_count": len(points),
            "last_ingested": max_timestamp,
        }


_qdrant_store: QdrantStore | None = None


def get_qdrant_store() -> QdrantStore:
    """Get or create QdrantStore singleton."""
    global _qdrant_store
    if _qdrant_store is None:
        _qdrant_store = QdrantStore(client=get_qdrant_client())
    return _qdrant_store
