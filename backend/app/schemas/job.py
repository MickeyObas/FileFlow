from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.job_status import JobStatus


class JobOut(BaseModel):
    id: UUID
    file_id: UUID
    status: JobStatus
    error_message: str | None
    result_payload: str | None
    result_storage_key: str | None
    retry_count: int
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None
    completed_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
