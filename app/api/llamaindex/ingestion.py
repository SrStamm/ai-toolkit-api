# Carga + chunking
# SimpleDirectoryReader
# SentenceSplitter

from pathlib import Path
import uuid
from llama_index.core import VectorStoreIndex
from llama_index.core.schema import TextNode
from llama_index.readers.file import PDFReader
from llama_index.core.node_parser import SentenceSplitter

from .config import setup_llamaindex
from ..extraction.cleaners.pdf_cleaner import PDFCleaner, CleanerInterface
from ..extraction.factory import SourceFactory

setup_llamaindex()

class LlamaIngester:
    def __init__(self):
        self.pdf_cleaner: CleanerInterface = PDFCleaner()
        self.parser = SentenceSplitter(chunk_size=512, chunk_overlap=100)

    def _store_data(self, nodes, storage_context):
        VectorStoreIndex(
            nodes,
            storage_context=storage_context
        )
        pass

    def ingest_pdf(
        self,
        pdf_path: str,
        source: str,
        domain: str,
        topic:str,
        storage_context
    ):
        reader = PDFReader()
        documents = reader.load_data(file=Path(pdf_path))

        for doc in documents:
            cleaned_text = self.pdf_cleaner.clean(doc.get_content())
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
        self._store_data(nodes, storage_context)

        return {
            "docuemtns": len(documents),
            "status": "indexed"
        }


    async def ingest_html(
        self,
        url: str,
        domain: str,
        topic:str,
        storage_context
    ):
        extractor, cleaner = SourceFactory.get_extractor_and_cleaner(url)

        content = await extractor.extract(url)
        cleaned_text = cleaner.clean(content)
        chunks = cleaner.chunk(cleaned_text)

        nodes = []

        for i, chunk in enumerate(chunks):
            unique_string = f"{url}_{i}"
            node_id = str(uuid.uuid5(uuid.NAMESPACE_URL, unique_string))

            node = TextNode(
                text=chunk.text,
                id_=node_id,
                metadata={
                    "source": url,
                    "filename": url,
                    "domain": domain,
                    "topic": topic,
                    "section": chunk.section or "General",
                }
            )
            nodes.append(node)

        self._store_data(nodes, storage_context)

        return {
            "source": url,
            "status": "indexed",
            "chunks": len(nodes)
        }
