# POST /llamaindex/ingest, POST /llamaindex/ask

from pathlib import Path
import shutil
import uuid
from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.api.rag.schemas import IngestRequest, QueryRequest, QueryResponse
from app.api.llamaindex.orchestrator import LlamaIndexOrchestrator, get_orchestrator

router = APIRouter(prefix="/llama", tags=["Llama"])


@router.post("/ingest")
def ingest_document(
    file: UploadFile = File(...),
    source: str = Form(...),
    domain: str = Form(...),
    topic: str = Form(...),
    serv: LlamaIndexOrchestrator = Depends(get_orchestrator),
):
    if not file.filename.lower().endswith(".pdf"):
        return {"status": "error", "message": "File must be a PDF"}

    id = uuid.uuid4()

    upload_path = Path("/backend/api_data") / f"{id}.pdf"
    upload_path.parent.mkdir(parents=True, exist_ok=True)

    with upload_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    serv.proccess_pdf(
        pdf_path=str(upload_path), source=file.filename, domain=domain, topic=topic
    )

    return {"status": "ingested", "filename": file.filename, "source": source}


@router.post("/ingest-html")
async def ingest_html(
    ing_req: IngestRequest,
    serv: LlamaIndexOrchestrator = Depends(get_orchestrator),
):
    await serv.proccess_html(
        url=ing_req.url, domain=ing_req.domain, topic=ing_req.topic
    )

    return {"status": "ingested", "url": ing_req.url}


@router.get("/ask")
def query_llama(text: str, serv: LlamaIndexOrchestrator = Depends(get_orchestrator)):
    response = serv.query(text)
    return {"response": str(response)}


@router.post("/ask-custom")
def custom_query_llama(
    query: QueryRequest, serv: LlamaIndexOrchestrator = Depends(get_orchestrator)
) -> QueryResponse:
    return serv.custom_query(query=query.text, domain=query.domain, topic=query.topic)
