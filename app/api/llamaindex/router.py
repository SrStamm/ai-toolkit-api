# POST /llamaindex/ingest, POST /llamaindex/ask

from pathlib import Path
import shutil
import uuid
from fastapi import APIRouter, Depends, File, Form, UploadFile

from .orchrestator import LlamaIndexOrchestrator, get_orchestrator

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

    upload_path = Path('/backend/api_data') / f"{id}.pdf"
    upload_path.parent.mkdir(parents=True, exist_ok=True)

    with upload_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    serv.proccess_pdf(pdf_path=str(upload_path))

    return {"status": "ingested", "filename": file.filename, "source": source}


@router.get("/ask")
def query_llama(
    text: str,
    serv: LlamaIndexOrchestrator = Depends(get_orchestrator)
):
    response = serv.query(text)
    return {"response": str(response)}
