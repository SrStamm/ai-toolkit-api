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
    soup = serv.extract_html(url)

    serv.ingest_document(soup=soup, source=url, domain=domain, topic=topic)

    return {"status": "ingested", "url": url}


@router.post("/retrieve")
def retrieve_search(
    text: str,
    serv: RAGService = Depends(get_rag_service),
):
    query_result = serv.query(text=text)

    return {"status": "query", "Points": query_result}
