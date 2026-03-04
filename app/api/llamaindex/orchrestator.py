from llama_index.core import VectorStoreIndex
from llama_index.core.postprocessor import SentenceTransformerRerank
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
        self.rerank = SentenceTransformerRerank(
            model="cross-encoder/mmarco-mMiniLMv2-L12-H384-v1",
            top_n=3
        )

    def proccess_pdf(self, pdf_path: str):
        storage_context = self.indexer.get_storage_context()
        response = self.ingester.ingest_pdf(pdf_path, storage_context)

        self.index = VectorStoreIndex.from_vector_store(
            vector_store=self.indexer.vectore_store,
        )

        return response

    def query(self, query: str):
        query_engine = self.index.as_query_engine(
            similarity_top_k=10,
            node_postprocessors=[self.rerank]
        )

        return query_engine.query(query)


_orchestrator_instance = None

def get_orchestrator():
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = LlamaIndexOrchestrator()
    return _orchestrator_instance

if __name__ == "__main__":
    orchrestator = LlamaIndexOrchestrator()
    # result = orchrestator.proccess_pdf("api/llamaindex/data/AI Engineering.pdf")
    result2 = orchrestator.query("¿Qué es la ingeniería de IA?")

    print(result2)
