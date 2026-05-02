"""
Reindex Document Tool.

Dispara una tarea de Celery para re-indexar un documento.
Elimina la versión anterior e ingesta la nueva desde la URL.
"""

from typing import Optional
import structlog

from .tools_registry import ToolRegistry, ToolResponse
from ...retrieval_engine.jobs.celery_tasks import reindex_document_task

logger = structlog.get_logger()


def _reindex_document_handler(
    source: str,
    url: str,
    domain: str,
    topic: str,
    **kwargs
) -> ToolResponse:
    """
    Handler para re-indexar un documento.
    Dispara una tarea asíncrona en Celery y devuelve el task_id.
    """
    try:
        # 1. Create job_id using JobService (Redis)
        from ...retrieval_engine.jobs.job_service import JobService
        job_serv = JobService()
        job_id = job_serv.create()

        logger.info("tool_reindex_start", source=source, url=url, job_id=job_id)

        # 2. Dispatch Celery task with job_id
        reindex_document_task.delay(job_id, source, url, domain, topic)

        msg = f"Re-indexing started for '{source}'. Job ID: {job_id}"
        logger.info("tool_reindex_dispatched", source=source, job_id=job_id)

        return ToolResponse(
            output=msg, 
            metadata={"task_id": job_id, "status": "processing", "source": source}
        )

    except Exception as e:
        logger.error("tool_reindex_error", source=source, error=str(e))
        return ToolResponse(
            output=f"Error starting re-index: {str(e)}",
            metadata={"error": str(e)},
        )


def register_reindex_document_tool() -> None:
    """Registra la tool en el registry."""
    ToolRegistry.register(
        name="reindex_document",
        description="Re-index a document from a URL. Deletes the old version and ingests the new one. Returns a task_id for tracking. Requires URL, source, domain, and topic.",
        parameters={
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "description": "The source identifier for the document",
                },
                "url": {
                    "type": "string",
                    "description": "The URL to fetch the new content from",
                },
                "domain": {
                    "type": "string",
                    "description": "The domain category (e.g., 'python', 'fastapi')",
                },
                "topic": {
                    "type": "string",
                    "description": "The topic category (e.g., 'routing', 'auth')",
                },
            },
            "required": ["source", "url", "domain", "topic"],
        },
        handler=_reindex_document_handler,
        # No dependencies needed, it dispatches to Celery
        dependencies=[],
    )
