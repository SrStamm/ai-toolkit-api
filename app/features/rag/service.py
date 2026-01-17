from fastapi import Depends
from app.core.llm_client import LLMClient, get_llm_client
import requests
from bs4 import BeautifulSoup
from app.features.rag.rag_client import RAGClient, get_rag_client


class RAGService:
    def __init__(self, llm_client: LLMClient, rag_client: RAGClient):
        self.llm_client = llm_client
        self.rag_client = rag_client

    def _clean_text(self, text: str) -> str:
        lines = [line.strip() for line in text.splitlines()]
        lines = [
            line for line in lines if len(line) > 30 and any(c.isalnum() for c in line)
        ]
        return "\n".join(lines)

    def extract_html(self, url: str):
        html = requests.get(url).text
        soup = BeautifulSoup(html, "html.parser")

        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        main = soup.find("main") or soup.find("article")

        if not main:
            raise ValueError("Not found main content")

        text = main.get_text(separator="\n")

        return self._clean_text(text)

    def chunk_text(self, text: str, max_chars=300, overlap=100):
        chunks = []
        start = 0

        while start < len(text):
            end = start + max_chars
            chunk = text[start:end]
            chunks.append(chunk)
            start = end - overlap

        return chunks

    def ingest_document(self, text, source, domain, topic):
        chunks = self.chunk_text(text)

        for chunk in chunks:
            payload = {
                "text": chunk,
                "source": source,
                "domain": domain,
                "topic": topic,
            }

            self.rag_client.insert_vector(chunk, payload)

    def query(self, text):
        chunks = self.rag_client.query(text)
        return chunks


def get_rag_service(
    llm_client: LLMClient = Depends(get_llm_client),
    rag_client: RAGClient = Depends(get_rag_client),
):
    return RAGService(llm_client, rag_client)
