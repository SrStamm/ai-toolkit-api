"""
Ingest PDF File Tool.

Dispara una tarea de Celery para ingestar un archivo PDF subido por el usuario.
Si el archivo ya existe en el vector store (mismo source), se re-indexa automáticamente.
"""

from pathlib import Path
import structlog

from .tools_registry import ToolRegistry, ToolResponse
from ...retrieval_engine.jobs.celery_tasks import ingest_file_job

logger = structlog.get_logger()

UPLOAD_DIR = Path("/backend/api_data") / "uploads"


def _ingest_pdf_file_handler(
    file_uuid: str,
    filename: str,
    domain: str,
    topic: str,
    **kwargs,
) -> ToolResponse:
    """
    Handler para ingestar un archivo PDF.

    Requiere file_uuid y filename (obtenidos tras subir el archivo).
    Si domain o topic faltan, devuelve error para que el router pida metadata.
    Dispara una tarea asíncrona en Celery y devuelve el task_id.
    """
    # ── Validación temprana de metadata ──────────────────────────────────
    missing = []
    if not domain:
        missing.append("domain")
    if not topic:
        missing.append("topic")
    if not file_uuid:
        missing.append("file_uuid")

    if missing:
        msg = (
            f"Cannot ingest: missing required metadata: {', '.join(missing)}. "
            "Please provide them and try again."
        )
        logger.warning("tool_ingest_pdf_missing_metadata", missing=missing, filename=filename)
        return ToolResponse(
            output=msg,
            metadata={"error": "missing_metadata", "missing_fields": missing},
        )

    # ── Validar que el archivo exista en disco ──────────────────────────
    file_path = UPLOAD_DIR / f"{file_uuid}.pdf"

    if not file_path.exists():
        msg = f"File '{filename}' not found on server (UUID: {file_uuid}). It may have expired."
        logger.error("tool_ingest_pdf_file_not_found", file_uuid=file_uuid, path=str(file_path))
        return ToolResponse(
            output=msg,
            metadata={"error": "file_not_found", "file_uuid": file_uuid},
        )

    try:
        # 1. Crear job_id usando JobService (Redis)
        from ...retrieval_engine.jobs.job_service import JobService
        job_serv = JobService()
        job_id = job_serv.create()

        logger.info(
            "tool_ingest_pdf_start",
            filename=filename,
            file_uuid=file_uuid,
            domain=domain,
            topic=topic,
            job_id=job_id,
        )

        # 2. Dispatch Celery task (reusa ingest_file_job existente)
        # ingest_file_job recibe: job_id, file_path, source, domain, topic
        ingest_file_job.delay(job_id, str(file_path), filename, domain, topic)

        msg = (
            f"Ingestion started for '{filename}'. "
            f"Job ID: {job_id}"
        )
        logger.info("tool_ingest_pdf_dispatched", filename=filename, job_id=job_id)

        return ToolResponse(
            output=msg,
            metadata={
                "task_id": job_id,
                "status": "processing",
                "source": filename,
            },
        )

    except Exception as e:
        logger.error("tool_ingest_pdf_error", filename=filename, error=str(e))
        return ToolResponse(
            output=f"Error starting ingestion: {str(e)}",
            metadata={"error": str(e)},
        )


def register_ingest_pdf_file_tool() -> None:
    """Registra la tool en el registry via auto-discovery."""
    ToolRegistry.register(
        name="ingest_pdf_file",
        description=(
            "Ingest an uploaded PDF file into the knowledge base. "
            "Use this when the user has uploaded a PDF file (file_uuid and filename are provided). "
            "If the document already exists, it will be re-indexed automatically. "
            "Returns a task_id for tracking progress. "
            "Requires: file_uuid (the upload identifier), filename (original file name), "
            "domain (category like 'python', 'fastapi', 'docker'), "
            "and topic (subcategory like 'routing', 'auth', 'deploy')."
        ),
        parameters={
            "type": "object",
            "properties": {
                "file_uuid": {
                    "type": "string",
                    "description": "The UUID returned after uploading the PDF file",
                },
                "filename": {
                    "type": "string",
                    "description": "The original filename of the uploaded PDF",
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
            "required": ["file_uuid", "filename", "domain", "topic"],
        },
        handler=_ingest_pdf_file_handler,
        dependencies=[],
    )
