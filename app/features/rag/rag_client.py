from uuid import uuid4
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams
from sentence_transformers import SentenceTransformer

qdrant = QdrantClient(host="qdrant", port=6333)

COLLECTION_NAME = "documents"


class RAGClient:
    def __init__(self, client: QdrantClient) -> None:
        self.client = client
        self.embed_model = SentenceTransformer("intfloat/multilingual-e5-small")

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

    def query(self, text: str):
        embedding = self.embed_model.encode(f"query: {text}", normalize_embeddings=True)
        return embedding.tolist()

    def insert_vector(
        self,
        chunk,
        payload,
    ):
        vector = self.embed(chunk)

        point = PointStruct(id=str(uuid4()), vector=vector, payload=payload)

        self.client.upsert(collection_name=COLLECTION_NAME, points=[point])


def get_rag_client() -> RAGClient:
    return RAGClient(qdrant)
