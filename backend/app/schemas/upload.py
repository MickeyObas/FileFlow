from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.file_status import FileStatus
from app.models.upload_session import UploadSession
from app.schemas.progress import upload_progress


class UploadCreate(BaseModel):
    original_filename: str
    content_type: str
    expected_size: int | None = Field(default=None, gt=0)


class UploadOut(BaseModel):
    id: UUID
    original_filename: str
    content_type: str
    expected_size: int | None
    status: FileStatus
    bytes_received: int
    bytes_total: int | None
    progress_percent: float | None
    file_id: UUID | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_session(cls, session: UploadSession) -> UploadOut:
        bytes_total, progress_percent = upload_progress(
            bytes_received=session.bytes_received,
            expected_size=session.expected_size,
        )
        return cls(
            id=session.id,
            original_filename=session.original_filename,
            content_type=session.content_type,
            expected_size=session.expected_size,
            status=session.status,
            bytes_received=session.bytes_received,
            bytes_total=bytes_total,
            progress_percent=progress_percent,
            file_id=session.file_id,
            created_at=session.created_at,
        )
