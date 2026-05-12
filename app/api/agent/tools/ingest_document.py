"""
Ingest Document Tool.

Dispara una tarea de Celery para ingestar (o re-indexar) un documento desde una URL.
Si el documento ya existe, elimina la versión anterior e ingesta la nueva.
"""

from typing import Optional
import structlog

from .tools_registry import ToolRegistry, ToolResponse
from ...retrieval_engine.jobs.celery_tasks import reindex_document_task

logger = structlog.get_logger()


def _ingest_document_handler(
    source: str,
    url: str,
    domain: str,
    topic: str,
    **kwargs
) -> ToolResponse:
    """
    Handler para ingestar un documento desde una URL.

    Si el documento ya existe (mismo source), se re-indexa automáticamente.
    Dispara una tarea asíncrona en Celery y devuelve el task_id.

    Valida que todos los metadatos requeridos estén presentes antes de enviar.
    """
    # ── Validación temprana de metadata ──────────────────────────────────
    missing = []
    if not source:
        missing.append("source")
    if not domain:
        missing.append("domain")
    if not topic:
        missing.append("topic")

    if missing:
        msg = f"Cannot ingest: missing required metadata: {', '.join(missing)}. Please provide them and try again."
        logger.warning("tool_ingest_missing_metadata", missing=missing, url=url)
        return ToolResponse(
            output=msg,
            metadata={"error": "missing_metadata", "missing_fields": missing},
        )

    try:
        # 1. Create job_id using JobService (Redis)
        from ...retrieval_engine.jobs.job_service import JobService
        job_serv = JobService()
        job_id = job_serv.create()

        logger.info("tool_ingest_start", source=source, url=url, job_id=job_id)

        # 2. Dispatch Celery task with job_id
        reindex_document_task.delay(job_id, source, url, domain, topic)

        msg = f"Ingestion started for '{source}'. Job ID: {job_id}"
        logger.info("tool_ingest_dispatched", source=source, job_id=job_id)

        return ToolResponse(
            output=msg,
            metadata={"task_id": job_id, "status": "processing", "source": source}
        )

    except Exception as e:
        logger.error("tool_ingest_error", source=source, error=str(e))
        return ToolResponse(
            output=f"Error starting ingestion: {str(e)}",
            metadata={"error": str(e)},
        )


def register_ingest_document_tool() -> None:
    """Registra la tool en el registry."""
    ToolRegistry.register(
        name="ingest_document",
        description=(
            "Ingest a document from a URL into the knowledge base. "
            "If the document already exists, it will be re-indexed automatically. "
            "Returns a task_id for tracking progress. "
            "Requires: url (the link), source (an identifier for the document), "
            "domain (category like 'python', 'fastapi', 'docker'), "
            "and topic (subcategory like 'routing', 'auth', 'deploy')."
        ),
        parameters={
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "description": "An identifier for the document (usually the URL or a short name)",
                },
                "url": {
                    "type": "string",
                    "description": "The URL to fetch the content from",
                },
                "domain": {
                    "type": "string",
                    "description": "The domain category (e.g., 'python', 'fastapi', 'docker')",
                },
                "topic": {
                    "type": "string",
                    "description": "The topic subcategory (e.g., 'routing', 'auth', 'deploy')",
                },
            },
            "required": ["source", "url", "domain", "topic"],
        },
        handler=_ingest_document_handler,
        # No dependencies needed, it dispatches to Celery
        dependencies=[],
    )
