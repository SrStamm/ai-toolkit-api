from fastapi import APIRouter, Depends
from app.features.rag.service import RAGService, get_rag_service

router = APIRouter(prefix="/rag")


@router.post("/ingest")
def ingest_document(url: str, serv: RAGService = Depends(get_rag_service)):
    return serv.extract_html(url)
