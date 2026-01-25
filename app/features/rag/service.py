from fastapi import Depends
import json
import structlog
from .prompt import PROMPT_TEMPLATE
from app.core.llm_client import LLMClient, get_llm_client
from app.features.extraction.source.html_source import HTMLSource
from app.features.extraction.source.readme_source import READMESource
from .rag_client import RAGClient, get_rag_client


log = structlog.get_logger()


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

    async def extract_from_url(self, url: str):
        html = await HTMLSource(
            only_main=True, allowed_tags=["h1", "h2", "p", "li"]
        ).extract(url)
        return self._clean_text(html)

    def chunk_html(self, soup):
        chunks = []

        intro = soup.split("\n")[0:5]
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

    def chunk_by_markdown(self, text: str):
        separated = text.split("##")

        if not separated[0].strip():
            separated.pop(0)

        return ["## " + s.strip().lstrip("#") for s in separated]

    async def ingest_document(self, url, source, domain, topic):
        if "raw.githubusercontent.com" in url:
            text = await READMESource().extract(url)
            chunks = self.chunk_by_markdown(text)
        else:
            text = await self.extract_from_url(url)
            chunks = self.chunk_text(text)

        points = []
        for i, chunk in enumerate(chunks):
            payload = {
                "text": chunk,
                "source": source,
                "domain": domain.lower(),
                "topic": topic.lower(),
                "chunk_index": i,
            }

            point = self.rag_client.create_point(chunk, payload)
            points.append(point)

        self.rag_client.insert_vector(points)

    def query(self, text, domain: str, topic: str):
        chunks = self.rag_client.query(text, domain.lower(), topic.lower())
        return chunks

    def ask(self, user_question: str, domain: str, topic: str):
        query_result = self.query(user_question, domain, topic)

        if not query_result:
            log.info(
                "NO RAG results",
                domain=domain,
                topic=topic,
                user_question=user_question,
            )

        log_info = [
            {"index": hit.payload["chunk_index"], "score": round(float(hit.score), 4)}
            for hit in query_result
        ]

        print(f"query_result: {log_info}")

        rerank_result = self.rag_client.rerank(user_question, query_result)

        log_info = [
            {"index": hit.payload["chunk_index"], "score": round(float(hit.score), 4)}
            for hit in rerank_result
        ]

        print(f"rerank_result: {log_info}")

        context = "\n\n".join(
            f"[{i + 1}]\n{chunk.payload['text']}"
            for i, chunk in enumerate(rerank_result)
        )

        prompt = PROMPT_TEMPLATE.format(context=context, question=user_question)

        raw = self.llm_client.generate_content(prompt)

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = {"answer": raw}

        seen = set()
        citations = []
        for q in query_result[:2]:
            src = q.payload["source"]
            if src in seen:
                continue
            seen.add(src)

            citations.append({"source": src, "chunk_index": q.payload["chunk_index"]})

        return {"response": parsed["answer"], "citations": citations}


def get_rag_service(
    llm_client: LLMClient = Depends(get_llm_client),
    rag_client: RAGClient = Depends(get_rag_client),
):
    return RAGService(llm_client, rag_client)
