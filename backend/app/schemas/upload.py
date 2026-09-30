from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.file_status import FileStatus


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
    file_id: UUID | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
