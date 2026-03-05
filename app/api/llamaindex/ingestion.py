# Carga + chunking
# SimpleDirectoryReader
# SentenceSplitter

from pathlib import Path
from llama_index.core import VectorStoreIndex
from llama_index.readers.file import PDFReader
from llama_index.core.node_parser import SentenceSplitter
from .config import setup_llamaindex
from ..extraction.cleaners.pdf_cleaner import PDFCleaner, CleanerInterface

setup_llamaindex()

class LlamaIngester:
    def __init__(self):
        self.cleaner: CleanerInterface = PDFCleaner()
        self.parser = SentenceSplitter(chunk_size=512, chunk_overlap=50)

    def ingest_pdf(self, pdf_path: str, source: str, domain: str, topic:str, storage_context):
        reader = PDFReader()
        documents = reader.load_data(file=Path(pdf_path))

        for doc in documents:
            cleaned_text = self.cleaner.clean(doc.get_content())
            doc.set_content(cleaned_text)
            doc.metadata.update({
                "domain": domain,
                "topic": topic,
                "filename": Path(pdf_path).name,
                "source": source
                }
            )

        nodes = self.parser.get_nodes_from_documents(documents)

        # Create index
        VectorStoreIndex(
            nodes,
            storage_context=storage_context
        )

        return {
            "docuemtns": len(documents),
            "status": "indexed"
        }

