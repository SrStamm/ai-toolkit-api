from typing import List
from uuid import uuid4
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
from sentence_transformers import SentenceTransformer, CrossEncoder

qdrant = QdrantClient(host="qdrant", port=6333)

COLLECTION_NAME = "documents"


class RAGClient:
    def __init__(self, client: QdrantClient) -> None:
        self.client = client
        self.embed_model = SentenceTransformer("intfloat/multilingual-e5-small")
        self.rerank_model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

    def create_collection(self):
        print(f"Verifying if exist collection {COLLECTION_NAME} exist")

        exists = self.client.collection_exists(COLLECTION_NAME)

        if exists:
            print("Colection exist")
            return

        try:
            self.client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=384, distance=Distance.COSINE),
            )

            print("Colection created with success")

        except Exception as e:
            print(f"Error al crear la colección: {e}")
            raise

    def embed(self, text: str):
        embedding = self.embed_model.encode(
            f"passage: {text}", normalize_embeddings=True
        )
        return embedding.tolist()

    def query(self, text: str, domain: str, topic: str):
        embedding = self.embed_model.encode(f"query: {text}", normalize_embeddings=True)
        embed_list = embedding.tolist()

        search_result = self.client.query_points(
            collection_name=COLLECTION_NAME,
            query=embed_list,
            with_payload=True,
            limit=10,
            query_filter=Filter(
                must=[
                    FieldCondition(key="domain", match=MatchValue(value=domain)),
                    FieldCondition(key="topic", match=MatchValue(value=topic)),
                ]
            ),
        ).points

        return search_result

    def create_point(self, chunk, payload) -> PointStruct:
        vector = self.embed(chunk)

        return PointStruct(id=str(uuid4()), vector=vector, payload=payload)

    def insert_vector(self, points: List[PointStruct], batch_size: int = 64):
        for i in range(0, len(points), batch_size):
            batch = points[i : i + batch_size]
            self.client.upsert(collection_name=COLLECTION_NAME, points=batch)

    def rerank(self, query: str, search_result: list) -> List[ScoredPoint]:
        # create pairs (question, text of chunk)
        pairs = [[query, hit.payload["text"]] for hit in search_result]

        # model give us a relevant points for each pair
        scores = self.rerank_model.predict(pairs)

        # match the score with your result
        for i, hit in enumerate(search_result):
            hit.score = scores[i]

        # sort from highest to lowest according to the new score
        search_result.sort(key=lambda x: x.score, reverse=True)

        return search_result[:3]


def get_rag_client() -> RAGClient:
    return RAGClient(qdrant)
