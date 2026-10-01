from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.job_status import JobStatus
from app.models.processing_job import ProcessingJob
from app.schemas.progress import job_progress_for_status


class JobOut(BaseModel):
    id: UUID
    file_id: UUID
    status: JobStatus
    stage: str | None
    progress_percent: int
    error_message: str | None
    result_payload: str | None
    result_storage_key: str | None
    retry_count: int
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None
    completed_at: datetime | None

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_job(cls, job: ProcessingJob) -> JobOut:
        stage, progress_percent = job_progress_for_status(
            status=job.status,
            stage=job.stage,
            stored_percent=job.progress_percent,
        )
        return cls(
            id=job.id,
            file_id=job.file_id,
            status=job.status,
            stage=stage,
            progress_percent=progress_percent,
            error_message=job.error_message,
            result_payload=job.result_payload,
            result_storage_key=job.result_storage_key,
            retry_count=job.retry_count,
            created_at=job.created_at,
            updated_at=job.updated_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
        )
