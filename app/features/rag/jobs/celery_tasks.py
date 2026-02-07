# celery tasks - wrapper

import asyncio

from .schemas import JobStatus
from .job_service import JobService
from ..providers.qdrant_client import qdrant_client
from ..providers.local_ai import get_embeddign_service
from ..service import RAGService
from ....core.celery_app import celery_app
from ....core.llm_client import get_llm_client


@celery_app.task(bind=True)
def ingest_html_job(self, job_id: str, ingest_data: dict):
    job_service = JobService()

    llm_client = get_llm_client()
    embed_service = get_embeddign_service()
    rag_service = RAGService(llm_client, qdrant_client, embed_service)

    try:
        job_service.update_status(job_id, JobStatus.running)
        job_service.update_progress(job_id, 10)

        async def tracker(percent, message):
            job_service.update_progress(job_id, percent)

        asyncio.run(
            rag_service.ingest_document(
                url=ingest_data["url"],
                source=ingest_data["url"],
                domain=ingest_data["domain"],
                topic=ingest_data["topic"],
                progress_callback=tracker,
            )
        )

        job_service.update_progress(job_id, 100)
        job_service.update_status(job_id, JobStatus.completed)

    except Exception as e:
        job_service.fail(job_id, str(e))
        raise
