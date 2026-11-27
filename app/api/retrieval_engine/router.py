import structlog
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.api.exceptions import ApiError
from app.domain.source_identity import make_pdf_source, source_lookup_keys
from .exceptions import InvalidFilterError, VectorStoreError
from .service import RAGService, get_rag_service
from .jobs.celery_tasks import ingest_file_job, ingest_html_job
from .jobs.job_service import JobService
from .schemas.request import IngestRequest, SearchRequest
from .schemas.response import (
    DeleteDocumentResponse,
    DocumentMetadataResponse,
    ErrorResponse,
    IngestJobResponse,
    JobStatusResponse,
    ListDocumentsResponse,
    SearchResponse,
)

router = APIRouter(prefix="/rag", tags=["RAG"])

logger = structlog.getLogger()

ERROR_DESCRIPTIONS: dict[int, str] = {
    400: "Bad request",
    404: "Resource not found",
    422: "Validation error",
    500: "Internal server error",
    503: "Vector store unavailable",
}


def documented_errors(*status_codes: int) -> dict[int, dict[str, object]]:
    """Build OpenAPI response documentation for the given status codes."""
    return {
        code: {"model": ErrorResponse, "description": ERROR_DESCRIPTIONS[code]}
        for code in status_codes
    }

@router.post(
    "/search",
    response_model=SearchResponse,
    responses=documented_errors(422, 500),
)
def search_documents(
    request: SearchRequest, rag_service: RAGService = Depends(get_rag_service)
):
    context, citations = rag_service.query.get_context(
        query=request.query,
        top_k=request.top_k,
        domain=request.domain,
        topic=request.topic,
    )

    return { "context": context, "citations": citations }

@router.post(
    "/documents",
    response_model=ListDocumentsResponse,
    responses=documented_errors(422, 500),
)
async def get_documents(
    domain: str | None = None, rag_service: RAGService = Depends(get_rag_service)
):
    sources = rag_service.vector_store.list_sources(domain)

    output_lines = [f"Found {len(sources)} document(s):"]
    for src in sources:
        display_name = src.get("display_name") or src["source"]
        output_lines.append(
            f"- {display_name} ({src['domain']}/{src['topic']}) - {src['chunk_count']} chunks"
        )

    return {
        "status": "success",
        "metadata":
            {
                "documents": sources,
                "count": len(sources)
            },
        "output": "\n".join(output_lines)
    }

@router.delete(
    "/documents/{source:path}",
    response_model=DeleteDocumentResponse,
    responses=documented_errors(400, 422, 500, 503),
)
async def delete_document(
    source: str, rag_service: RAGService = Depends(get_rag_service)
):
    try:
        for key in source_lookup_keys(source):
            rag_service.vector_store.delete_by_filter({"source": key})
    except InvalidFilterError as exc:
        raise ApiError(
            status_code=400,
            code="invalid_filter",
            message=str(exc),
            retryable=False,
        ) from exc
    except VectorStoreError as exc:
        raise ApiError(
            status_code=503,
            code="vector_store_error",
            message="Vector store unavailable",
            retryable=True,
        ) from exc
    return {"status": "deleted", "source": source}

@router.get(
    "/documents/metadata",
    response_model=DocumentMetadataResponse,
    responses=documented_errors(404, 422, 500),
)
async def get_documents_metadata(
    source: str, rag_service: RAGService = Depends(get_rag_service)
):
    metadata = None
    for key in source_lookup_keys(source):
        metadata = rag_service.vector_store.get_source_metadata(key)
        if metadata is not None:
            break

    if metadata is None:
        raise ApiError(
            status_code=404,
            code="document_not_found",
            message=f"Document not found: {source}",
            retryable=False,
        )

    output_str = (
        f"Source: {metadata['source']}\n"
        f"Domain: {metadata['domain']}\n"
        f"Topic: {metadata['topic']}\n"
        f"Chunks: {metadata['chunk_count']}\n"
        f"Last Ingested: {metadata['last_ingested']}"
    )

    return { "status": "success", "metadata": metadata, "output": output_str}

@router.post(
    "/ingest/job",
    response_model=IngestJobResponse,
    responses=documented_errors(422, 500),
)
async def ingest_document_job(
    ingest: IngestRequest, job_serv: JobService = Depends(JobService)
):
    job_id = job_serv.create()

    ingest_html_job.delay(job_id, ingest.model_dump())

    return {"status": "queued", "job_id": job_id}

@router.post(
    "/ingest-file/job",
    response_model=IngestJobResponse,
    responses=documented_errors(400, 422, 500),
)
async def ingest_file_job_endpoint(
    file: UploadFile = File(...),
    domain: str = Form(...),
    topic: str = Form(...),
    replaces_source: str | None = Form(None),
    job_serv: JobService = Depends(JobService),
):
    if not (file.filename or "").lower().endswith(".pdf"):
        raise ApiError(
            status_code=400,
            code="invalid_file_type",
            message="File must be a PDF",
            retryable=False,
        )

    # create job_id
    job_id = job_serv.create()

    # Define route in shared volume
    upload_path = Path("/backend/api_data") / f"{job_id}.pdf"
    upload_path.parent.mkdir(parents=True, exist_ok=True)

    # Save file and derive its content-based identity
    content = await file.read()
    with upload_path.open("wb") as buffer:
        buffer.write(content)

    # create task
    ingest_file_job.delay(
        job_id=job_id,
        file_path=str(upload_path),
        source=make_pdf_source(content),
        domain=domain,
        topic=topic,
        display_name=file.filename,
        replaces_source=replaces_source,
    )

    # return status and job_id
    return {"status": "queued", "job_id": job_id}

@router.get(
    "/job/{job_id}",
    response_model=JobStatusResponse,
    responses=documented_errors(404, 422, 500),
)
async def get_status_job(job_id: str, job_serv: JobService = Depends(JobService)):
    try:
        return job_serv.get_state(job_id)
    except ValueError as exc:
        raise ApiError(
            status_code=404,
            code="job_not_found",
            message=f"Job not found: {job_id}",
            retryable=False,
        ) from exc
