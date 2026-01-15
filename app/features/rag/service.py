from fastapi import Depends
from app.core.llm_client import LLMClient, get_llm_client
import requests
from bs4 import BeautifulSoup


class RAGService:
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

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


def get_rag_service(
    llm_client: LLMClient = Depends(get_llm_client),
):
    return RAGService(llm_client)
