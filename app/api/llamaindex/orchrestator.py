from llama_index.core import VectorStoreIndex
from .ingestion import LlamaIngester
from .indexing import LlamaIndexer
from .config import setup_llamaindex

setup_llamaindex()

class LlamaIndexOrchestrator:
    def __init__(self):
        self.indexer = LlamaIndexer()
        self.ingester = LlamaIngester()
        self.index = VectorStoreIndex.from_vector_store(
            vector_store=self.indexer.vectore_store,
        )

    def proccess_pdf(self, pdf_path: str):
        storage_context = self.indexer.get_storage_context()
        response = self.ingester.ingest_pdf(pdf_path, storage_context)

        self.index = VectorStoreIndex.from_vector_store(
            vector_store=self.indexer.vectore_store,
        )

        return response

    def query(self, query: str):
        query_engine = self.index.as_query_engine()

        return query_engine.query(query)


if __name__ == "__main__":
    orchrestator = LlamaIndexOrchestrator()
    # result = orchrestator.proccess_pdf("api/llamaindex/data/AI Engineering.pdf")
    result2 = orchrestator.query("¿Qué es la ingeniería de IA?")

    print(result2)
