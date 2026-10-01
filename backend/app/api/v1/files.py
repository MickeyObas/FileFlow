from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.file_status import FileStatus
from app.schemas.file import FileOut
from app.services import file_service, idempotency_service

DbSession = Annotated[Session, Depends(get_db)]
IdempotencyKeyHeader = Annotated[str | None, Header(alias="Idempotency-Key")]


router = APIRouter(
    prefix="/files",
    tags=["Files"],
)


@router.get("/{file_id}", response_model=FileOut)
def get_file(file_id: UUID, db: DbSession):
    file = file_service.get_file(db, file_id)

    if file is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

    return file


@router.get("/", response_model=list[FileOut])
def get_files(db: DbSession, status: FileStatus | None = None):
    return file_service.get_files(db, status=status)


@router.post("/", response_model=FileOut)
def upload_file(
    uploaded_file: UploadFile,
    db: DbSession,
    idempotency_key: IdempotencyKeyHeader = None,
):
    return file_service.create_file(
        db,
        uploaded_file,
        idempotency_key=idempotency_service.normalize_key(idempotency_key),
    )


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
