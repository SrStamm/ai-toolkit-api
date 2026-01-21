from fastapi import APIRouter, Depends
from app.features.rag.schemas import IngestRequest, QueryRequest
from app.features.rag.service import RAGService, get_rag_service

router = APIRouter(prefix="/rag", tags=["RAG"])


@router.post("/ingest")
def ingest_document(
    ingest: IngestRequest,
    serv: RAGService = Depends(get_rag_service),
):
    soup = serv.extract_html(ingest.url)

    serv.ingest_document(
        soup=soup, source=ingest.url, domain=ingest.domain, topic=ingest.topic
    )

    return {"status": "ingested", "url": ingest.url}


@router.post("/retrieve")
def retrieve_search(
    query: QueryRequest,
    serv: RAGService = Depends(get_rag_service),
):
    query_result = serv.query(text=query.text, domain=query.domain, topic=query.topic)

    return {"status": "query", "Points": query_result}


@router.post("/ask")
def ask(
    query: QueryRequest,
    serv: RAGService = Depends(get_rag_service),
):
    return serv.ask(query.text, query.domain, query.topic)
