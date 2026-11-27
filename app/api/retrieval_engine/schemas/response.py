from typing import Literal
from pydantic import BaseModel

from ..jobs.schemas import JobStatus

class IngestJobResponse(BaseModel):
    status: Literal["queued"]
    job_id: str

class JobStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    progress: int | None = None
    step: str
    error: str | None = None

class SourceMetadata(BaseModel):
  source: str
  display_name: str | None = None
  domain: str
  topic: str
  chunk_count: int
  last_ingested: int

class SearchResponse(BaseModel):
    context: str
    citations: list[str]

class ListDocumentsMetadata(BaseModel):
  documents: list[SourceMetadata]
  count: int

class ListDocumentsResponse(BaseModel):
    status: Literal["success"]
    metadata: ListDocumentsMetadata
    output: str

class DocumentMetadataResponse(BaseModel):
    status: Literal["success"]
    metadata: SourceMetadata
    output: str

class DeleteDocumentResponse(BaseModel):
  status: Literal["deleted"]
  source: str

# Modelo general para errores
class ErrorResponse(BaseModel):
    code: str
    message: str
    retryable: bool = False
