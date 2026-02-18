import asyncio
import json
import shutil
from pathlib import Path
from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import StreamingResponse
import structlog

from .jobs.celery_tasks import ingest_file_job, ingest_html_job
from .jobs.job_service import JobService
from ..extraction.exceptions import EmptySourceContentError
from ..rag.exceptions import ChunkingError, EmbeddingError, error_event
from .schemas import IngestRequest, QueryRequest, QueryResponse
from .service import RAGService, get_rag_service

router = APIRouter(prefix="/rag", tags=["RAG"])

logger = structlog.getLogger()


@router.post(
    "/ingest",
    description="""
    It ingests documentation from a URL (it can be an HTML or a README) and adds it to a vector database.
    The variables of 'domain' and 'topic' allows to better separate the topics and gives better context to later.
    """,
)
async def ingest_document(
    ingest: IngestRequest,
    serv: RAGService = Depends(get_rag_service),
):
    await serv.ingest_document(
        url=ingest.url, source=ingest.url, domain=ingest.domain, topic=ingest.topic
    )

    return {"status": "ingested", "url": ingest.url}


@router.post(
    "/ingest-stream",
    description="""
    It ingests documentation from a URL (it can be an HTML or a README) and adds it to a vector database.
    The variables of 'domain' and 'topic' allows to better separate the topics and gives better context to later.
    """,
)
async def ingest_document_stream(
    ingest: IngestRequest,
    serv: RAGService = Depends(get_rag_service),
):
    async def generate():
        try:
            async for event in serv.ingest_document_stream(
                url=ingest.url,
                source=ingest.url,
                domain=ingest.domain,
                topic=ingest.topic,
            ):
                yield f"data: {json.dumps(event)}\n\n"
        except EmptySourceContentError:
            yield error_event(
                message="Document is empty after cleaning", recoverable=False
            )

        except ChunkingError:
            yield error_event(message="Failed to split document", recoverable=False)

        except EmbeddingError as e:
            yield error_event(message=f"Embedding failed: {str(e)}", recoverable=True)

        except asyncio.TimeoutError:
            yield error_event(
                message="Processing timed out, try a smaller document",
                recoverable=False,
            )

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/ingest-pdf")
async def ingest_pdf(
    file: UploadFile = File(...),
    source: str = Form(...),
    domain: str = Form(...),
    topic: str = Form(...),
    serv: RAGService = Depends(get_rag_service),
):
    if not file.filename.lower().endswith(".pdf"):
        return {"status": "error", "message": "File must be a PDF"}

    await serv.ingest_pdf_file(file=file, source=source, domain=domain, topic=topic)

    return {"status": "ingested", "filename": file.filename, "source": source}


@router.post("/ingest-pdf-stream")
async def ingest_pdf_stream(
    file: UploadFile = File(...),
    source: str = Form(...),
    domain: str = Form(...),
    topic: str = Form(...),
    serv: RAGService = Depends(get_rag_service),
):
    # Validación
    if not file.filename.lower().endswith(".pdf"):

        async def error_gen():
            yield error_event(message="File must be a PDF", recoverable=False)

        return StreamingResponse(error_gen(), media_type="text/event-stream")

    # Streaming
    async def generate():
        try:
            async for event in serv.ingest_pdf_file_stream(
                file=file, source=source, domain=domain, topic=topic
            ):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            yield error_event(message=str(e), recoverable=False)

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post(
    "/retrieve",
    description="""
    You can try to get context directly from the vector database.
    It is filtered by 'domain' and 'topic' in the database to return data.
    It is necessary to complete correctly.
    """,
)
def retrieve_search(
    query: QueryRequest,
    serv: RAGService = Depends(get_rag_service),
):
    query_result = serv.query(text=query.text, domain=query.domain, topic=query.topic)

    return {"status": "query", "Points": query_result}


@router.post(
    "/ask",
    description="""
    Ask to LLM about documentation previously charged and get a response with context
    """,
)
def ask(
    request: Request,
    query: QueryRequest,
    serv: RAGService = Depends(get_rag_service),
) -> QueryResponse:
    return serv.ask(request.state.session_id, query.text, query.domain, query.topic)


@router.post("/ask-stream")
async def ask_stream(
    request: Request,
    query: QueryRequest,
    serv: RAGService = Depends(get_rag_service),
):
    return StreamingResponse(
        serv.chat_stream(
            request.state.session_id, query.text, query.domain, query.topic
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


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
    job_serv: JobService = Depends(JobService)
):
    if not file.filename.lower().endswith(".pdf"):
        return {"status": "error", "message": "File must be a PDF"}


    # create job_id
    job_id = job_serv.create()

    # Define route in shared volume
    upload_path = Path('/backend/api_data') / f"{job_id}.pdf"
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
    except ValueError as e:
        return {"error": str(e)}, 404
