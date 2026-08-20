import structlog
import shutil
from pathlib import Path
from ..agent.adapters.rag_adapter import QueryServiceAdapter, create_query_adapter
from ..llamaindex_adapter.orchestrator import LlamaIndexOrchestrator
from ..retrieval_engine.service import get_rag_service
from fastapi import APIRouter, Depends, File, Form, UploadFile

from .jobs.celery_tasks import ingest_file_job, ingest_html_job
from .jobs.job_service import JobService
from .schemas import IngestRequest, SearchRequest

router = APIRouter(prefix="/rag", tags=["RAG"])

logger = structlog.getLogger()

# Use RAG service with adapter (retrieval_engine/)
rag_service = get_rag_service()
rag_adapter = create_query_adapter(rag_service)

@router.post("/search")
def search_documents(
        request: SearchRequest,
    ):

    return rag_adapter.get_context(request.query, request.top_k, request.domain)

@router.post(
    "/ingest/job",
)
async def ingest_document_job(
    ingest: IngestRequest, job_serv: JobService = Depends(JobService)
):
    job_id = job_serv.create()

    ingest_html_job.delay(job_id, ingest.model_dump())

    return {"status": "queued", "url": ingest.url, "job_id": job_id}


@router.post(
    "/ingest-file/job",
)
async def ingest_file_job_endpoint(
    file: UploadFile = File(...),
    source: str = Form(...),
    domain: str = Form(...),
    topic: str = Form(...),
    job_serv: JobService = Depends(JobService),
):
    if not file.filename.lower().endswith(".pdf"):
        return {"status": "error", "message": "File must be a PDF"}

    # create job_id
    job_id = job_serv.create()

    # Define route in shared volume
    upload_path = Path("/backend/api_data") / f"{job_id}.pdf"
    upload_path.parent.mkdir(parents=True, exist_ok=True)

    # Save file
    with upload_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # create task
    ingest_file_job.delay(job_id, str(upload_path), file.filename, domain, topic)

    # return status and job_id
    return {"status": "queued", "job_id": job_id}


@router.get(
    "/job/{job_id}",
)
async def get_status_job(job_id: str, job_serv: JobService = Depends(JobService)):
    try:
        state = job_serv.get_state(job_id)
        return state
    except Exception as e:
        return {"error": f"Job {job_id} not found"}, 404
