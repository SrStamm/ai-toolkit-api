from fastapi import APIRouter, Depends
from app.features.rag.service import RAGService, get_rag_service

router = APIRouter(prefix="/rag", tags=["RAG"])


@router.post("/ingest")
def ingest_document(
    url: str,
    domain: str = "general",
    topic: str = "unknown",
    serv: RAGService = Depends(get_rag_service),
):
    text = serv.extract_html(url)

    serv.ingest_document(text=text, source=url, domain=domain, topic=topic)

    return {"status": "ingested", "chunks": len(serv.chunk_text(text)), "url": url}
