# celery tasks - wrapper

import asyncio

import structlog

from .schemas import JobStatus
from .job_service import JobService
from ..service import RAGService, get_rag_service
from ....core.celery_app import celery_app

logger = structlog.get_logger()


@celery_app.task(bind=True)
def ingest_html_job(self, job_id: str, ingest_data: dict):
    job_service = JobService()
    rag_service: RAGService = get_rag_service()

    logger.info("ingest_job_started", job_id=job_id, url=ingest_data.get("url"))

    try:
        job_service.update_status(job_id, JobStatus.running)
        job_service.update_progress(job_id, 10)

        async def tracker(percent, message):
            logger.info(
                "ingest_job_progress", job_id=job_id, progress=percent, step=message
            )
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

        logger.info("ingest_job_success", job_id=job_id)

        job_service.update_progress(job_id, 100)
        job_service.update_status(job_id, JobStatus.completed)

    except Exception as e:
        logger.error("ingest_job_failed", job_id=job_id, error=str(e), exc_info=True)
        job_service.fail(job_id, str(e))
        raise
