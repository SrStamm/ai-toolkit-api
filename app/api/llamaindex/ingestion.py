# Carga + chunking
# SimpleDirectoryReader
# SentenceSplitter

from pathlib import Path
from llama_index.core import VectorStoreIndex
from llama_index.readers.file import PDFReader
from .config import setup_llamaindex

setup_llamaindex()

class LlamaIngester:
    def ingest_pdf(self, pdf_path: str, storage_context):
        # Load document
        reader = PDFReader()
        documents = reader.load_data(file=Path(pdf_path))

        # Create index
        VectorStoreIndex.from_documents(
            documents,
            storage_context=storage_context
        )

        return {
            "docuemtns": len(documents),
            "status": "indexed"
        }

