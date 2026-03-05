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
from ..extraction.cleaners.html_cleaner import HTMLCleaner
from ..extraction.source.html_source import HTMLSource

setup_llamaindex()

class LlamaIngester:
    def __init__(self):
        self.pdf_cleaner: CleanerInterface = PDFCleaner()
        self.html_cleaner = HTMLCleaner()
        self.html_source = HTMLSource()
        self.parser = SentenceSplitter(chunk_size=512, chunk_overlap=50)

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
        VectorStoreIndex(
            nodes,
            storage_context=storage_context
        )

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

        content = await self.html_source.extract(url=url)
        cleaned_text = self.html_cleaner.clean(content)

        chunks = self.html_cleaner.chunk(cleaned_text)

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

        VectorStoreIndex(
            nodes,
            storage_context=storage_context
        )

        return {
            "source": url,
            "status": "indexed",
            "chunks": len(nodes)
        }
