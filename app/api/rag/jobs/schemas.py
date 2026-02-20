# celery schemas
from enum import Enum
from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class JobStatus(str, Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"


class JobCreate(BaseModel):
    job_type: str


class JobState(BaseModel):
    job_id: str
    status: JobStatus
    step: str
    progress: Optional[int] = None
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime
