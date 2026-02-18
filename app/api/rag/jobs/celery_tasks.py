# celery tasks - wrapper

import asyncio
import os
import time

from fastapi import UploadFile
import structlog

from .schemas import JobStatus
from .job_service import JobService
from ..service import RAGService, get_rag_service
from ....core.celery_app import celery_app
from ....infrastructure.metrics import (
    celery_task_duration_seconds, 
    celery_tasks_total,
    documents_ingested_total,
)

logger = structlog.get_logger()


@celery_app.task(bind=True)
def ingest_html_job(self, job_id: str, ingest_data: dict):
    job_service = JobService()
    rag_service: RAGService = get_rag_service()

    task_start = time.perf_counter()

    logger.info("ingest_job_started", job_id=job_id, url=ingest_data.get("url"))

    try:
        job_service.update_status(job_id, JobStatus.running)
        job_service.update_progress(job_id, 10)

        async def tracker(percent, message):
            logger.info(
                "ingest_job_progress", job_id=job_id, progress=percent, step=message
            )
            job_service.update_progress(job_id, percent, message)

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

        celery_tasks_total.labels('ingest_html_job', 'success').inc()

    except Exception as e:
        celery_tasks_total.labels('ingest_html_job', 'error').inc()
        documents_ingested_total.labels(source_type='url', status='error').inc()
        logger.error("ingest_job_failed", job_id=job_id, error=str(e), exc_info=True)
        job_service.fail(job_id, str(e))
        raise
    finally:
        task_end = time.perf_counter() - task_start
        celery_task_duration_seconds.labels('ingest_html_job').observe(task_end)



@celery_app.task(bind=True)
def ingest_file_job(self, job_id: str, file_path: str, source, domain: str, topic: str):
    job_service = JobService()
    rag_service: RAGService = get_rag_service()

    task_start = time.perf_counter()
    logger.info("ingest_job_started", job_id=job_id, file_path=file_path)

    try:
        job_service.update_status(job_id, JobStatus.running)

        async def tracker(percent, message):
            logger.info(
                "ingest_job_progress", job_id=job_id, progress=percent, step=message
            )
            job_service.update_progress(job_id, percent, message)

        with open(file_path, "rb") as f:
            fake_upload_file = UploadFile(
                file=f, 
                filename=os.path.basename(file_path)
            )

            asyncio.run(
                rag_service.ingest_pdf_file(
                    file=fake_upload_file,
                    source=source,
                    domain=domain,
                    topic=topic,
                    progress_callback=tracker
                )
            )


        logger.info("ingest_job_success", job_id=job_id)

        celery_tasks_total.labels('ingest_file_job', 'success').inc()

        job_service.update_progress(job_id, 100)
        job_service.update_status(job_id, JobStatus.completed)

    except Exception as e:
        logger.error("ingest_job_failed", job_id=job_id, error=str(e), exc_info=True)
        job_service.fail(job_id, str(e))
        celery_tasks_total.labels('ingest_file_job', 'error').inc()
        documents_ingested_total.labels(source_type='pdf', status='error').inc()
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

        task_end = time.perf_counter() - task_start
        celery_task_duration_seconds.labels('ingest_file_job').observe(task_end)
