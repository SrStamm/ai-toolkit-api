# Carga + chunking
# SimpleDirectoryReader
# SentenceSplitter

from pathlib import Path
from llama_index.core import Settings, VectorStoreIndex
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.readers.file import PDFReader

Settings.embed_model = HuggingFaceEmbedding(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

class LlamaIngester:
    def ingest_pdf(self, pdf_path: str):
        # Load document
        reader = PDFReader()
        documents = reader.load_data(file=Path(pdf_path))

        # Create index
        index = VectorStoreIndex.from_documents(documents)

        return index

if __name__ == "__main__":
    ingester = LlamaIngester()
    index = ingester.ingest_pdf("/home/mirko/Documentos/proyectos/ai-toolkit-api/app/api/llamaindex/data/AI Engineering.pdf")

    print("PDF indexado correctamente")
    print(index)
