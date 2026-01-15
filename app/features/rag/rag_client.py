from uuid import UUID
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

qdrant = QdrantClient(host="qdrant", port=6333)

COLLECTION_NAME = "documents"


class RAGClient:
    def __init__(self, client: QdrantClient) -> None:
        self.client = client

    def create_collection(self):
        print(f"Verifying if exist collection {COLLECTION_NAME} exist")

        exists = self.client.collection_exists(COLLECTION_NAME)

        if exists:
            print("Colection exist")
            return

        try:
            self.client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=100, distance=Distance.COSINE),
            )

            print("Colection created with success")

        except Exception as e:
            print(f"Error al crear la colección: {e}")
            raise

    def insert_vector(
        self,
        vector,
        payload,
    ):
        point = PointStruct(id=UUID, vector=vector, payload=payload)

        self.client.upsert(collection_name=COLLECTION_NAME, points=[point])


def get_rag_client() -> RAGClient:
    return RAGClient(qdrant)
