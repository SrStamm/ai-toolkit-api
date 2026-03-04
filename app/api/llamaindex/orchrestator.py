from .ingestion import LlamaIngester
from .indexing import LlamaIndexer

class LlamaIndexOrchestrator:
    def __init__(self):
        self.indexer = LlamaIndexer()
        self.ingester = LlamaIngester()

    def proccess_pdf(self, pdf_path: str):
        storage_context = self.indexer.get_storage_context()
        return self.ingester.ingest_pdf(pdf_path, storage_context)


if __name__ == "__main__":
    orchrestator = LlamaIndexOrchestrator()
    result = orchrestator.proccess_pdf("api/llamaindex/data/AI Engineering.pdf")

    print("PDF indexado correctamente")
    print(result)
