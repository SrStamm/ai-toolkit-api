# state and lifecycle of jobs
from datetime import datetime
from uuid import uuid4

from .schemas import JobState, JobStatus
from ....core.redis import redis_client


class JobService:
    def get_state(self, job_id: str) -> JobState:
        json_data_from_redis = redis_client.get(f"job:{job_id}")

        if not json_data_from_redis:
            raise ValueError(f"Job {job_id} not found")

        state = JobState.model_validate_json(json_data_from_redis)
        return state

    def _set_state(self, job_id: str, state: str):
        redis_client.set(f"job:{job_id}", value=state, ex=48200)

    def generate_id(self) -> str:
        return str(uuid4())

    def create(self) -> str:
        job_id = self.generate_id()
        state = JobState(
            job_id=job_id,
            status=JobStatus.queued,
            progress=0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        self._set_state(job_id, state.model_dump_json())
        return job_id

    def update_status(self, job_id: str, status: JobStatus):
        state = self.get_state(job_id)
        state.status = status
        state.updated_at = datetime.now()
        self._set_state(job_id, state.model_dump_json())

    def update_progress(self, job_id: str, progress: int):
        state = self.get_state(job_id)
        state.progress = progress
        state.updated_at = datetime.now()
        self._set_state(job_id, state.model_dump_json())

    def fail(self, job_id: str, error: str):
        state = self.get_state(job_id)
        state.status = JobStatus.failed
        state.error = error
        state.updated_at = datetime.now()
        self._set_state(job_id, state.model_dump_json())
