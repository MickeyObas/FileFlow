from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.file_status import FileStatus
from app.schemas.file import FileDetailOut, FileOut
from app.schemas.job import JobOut
from app.services import file_service, idempotency_service, job_service

DbSession = Annotated[Session, Depends(get_db)]
IdempotencyKeyHeader = Annotated[str | None, Header(alias="Idempotency-Key")]


router = APIRouter(
    prefix="/files",
    tags=["Files"],
)


@router.get("/{file_id}/job", response_model=JobOut)
def get_file_job(file_id: UUID, db: DbSession):
    if file_service.get_file(db, file_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )
    job = job_service.get_job_for_file(db, file_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Processing job not found for this file",
        )
    return JobOut.from_job(job)


@router.get("/{file_id}", response_model=FileDetailOut)
def get_file(file_id: UUID, db: DbSession):
    row = file_service.get_file_with_job(db, file_id)

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

    file, job = row
    return FileDetailOut.from_file(file, processing_job=job)


@router.get("/", response_model=list[FileOut])
def get_files(db: DbSession, status: FileStatus | None = None):
    return file_service.get_files(db, status=status)


@router.post("/", response_model=FileDetailOut)
def upload_file(
    uploaded_file: UploadFile,
    db: DbSession,
    idempotency_key: IdempotencyKeyHeader = None,
):
    file = file_service.create_file(
        db,
        uploaded_file,
        idempotency_key=idempotency_service.normalize_key(idempotency_key),
    )
    row = file_service.get_file_with_job(db, file.id)
    assert row is not None
    file, job = row
    return FileDetailOut.from_file(file, processing_job=job)


@router.patch("/")
def update_file():
    pass


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_file(file_id: UUID, db: DbSession):
    deleted = file_service.delete_file(db, file_id=file_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )
