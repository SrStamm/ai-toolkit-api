from fastapi import Depends
from app.core.llm_client import LLMClient, get_llm_client
import requests
import json
from bs4 import BeautifulSoup
from app.features.rag.rag_client import RAGClient, get_rag_client

PROMPT_TEMPLATE = """
You are an expert assistant.

Answer the user's question using the information provided in the context below.
You may rephrase, summarize, or explain the content in your own words,
but do not add information that is not supported by the context.

Return ONLY valid JSON, without markdown or explanation.
Format:
{
  "answer": string
}


If the context does not contain enough information to answer the question,
say clearly that you do not have enough information.

Be clear, concise, and accurate.

Context:
---------
{context}
---------

Question:
{question}
"""


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

        return main

    def chunk_html(self, soup):
        chunks = []

        intro = soup.get_text().split("\n")[0:5]
        chunks.append("\n".join(intro))

        for section in soup.find_all(["h2", "h3"]):
            content = []
            for sib in section.find_next_siblings():
                if sib.name in ["h2", "h3"]:
                    break
                content.append(sib.get_text())

            text = section.get_text() + "\n" + "\n".join(content)
            chunks.append(text.strip())

        return chunks

    def chunk_text(self, text: str, max_chars=300, overlap=100):
        chunks = []
        start = 0

        while start < len(text):
            end = start + max_chars
            chunk = text[start:end]
            chunks.append(chunk)
            start = end - overlap

        return chunks

    def ingest_document(self, soup, source, domain, topic):
        chunks = self.chunk_html(soup)

        points = []
        for i, chunk in enumerate(chunks):
            payload = {
                "text": chunk,
                "source": source,
                "domain": domain,
                "topic": topic,
                "chunk_index": i,
            }

            point = self.rag_client.create_point(chunk, payload)
            points.append(point)

        self.rag_client.insert_vector(points)

    def query(self, text, domain: str, topic: str):
        chunks = self.rag_client.query(text, domain, topic)
        return chunks

    def ask(self, user_question: str, domain: str, topic: str):
        query_result = self.query(user_question, domain, topic)

        context = "\n\n".join(
            f"[{i + 1}]\n{chunk.payload['text']}"
            for i, chunk in enumerate(query_result)
        )

        prompt = PROMPT_TEMPLATE.format(context=context, question=user_question)

        raw = self.llm_client.generate_content(prompt)

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = {"answer": raw}

        return {"response": parsed["answer"], "context": query_result}


def get_rag_service(
    llm_client: LLMClient = Depends(get_llm_client),
    rag_client: RAGClient = Depends(get_rag_client),
):
    return RAGService(llm_client, rag_client)
