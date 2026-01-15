from fastapi import Depends
from app.core.llm_client import LLMClient, get_llm_client
import requests
from bs4 import BeautifulSoup


class RAGService:
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    def extract_html(self, url: str):
        html = requests.get(url).text
        soup = BeautifulSoup(html, "html.parser")

        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        main = soup.find("main") or soup.find("article")

        if not main:
            raise ValueError("Not found main content")

        text = main.get_text(separator="\n")

        return text


def get_rag_service(
    llm_client: LLMClient = Depends(get_llm_client),
):
    return RAGService(llm_client)
