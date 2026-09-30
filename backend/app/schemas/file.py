from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.file_status import FileStatus


class FileBase(BaseModel):
    original_filename: str
    content_type: str


class FileCreate(FileBase):
    pass


class FileUpdate(BaseModel):
    original_filename: str
    status: Optional[FileStatus] = None


class FileOut(FileBase):
    id: UUID
    status: FileStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
