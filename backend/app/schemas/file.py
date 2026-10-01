from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.file import File
from app.models.file_status import FileStatus
from app.models.processing_job import ProcessingJob
from app.schemas.job import JobOut


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
    size: int
    status: FileStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FileDetailOut(FileBase):
    id: UUID
    size: int
    status: FileStatus
    created_at: datetime
    processing_job: JobOut | None

    @classmethod
    def from_file(
        cls,
        file: File,
        *,
        processing_job: ProcessingJob | None,
    ) -> FileDetailOut:
        return cls(
            id=file.id,
            original_filename=file.original_filename,
            content_type=file.content_type,
            size=file.size,
            status=file.status,
            created_at=file.created_at,
            processing_job=(
                JobOut.from_job(processing_job) if processing_job is not None else None
            ),
        )
