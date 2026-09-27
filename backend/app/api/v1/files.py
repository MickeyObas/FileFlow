from fileinput import FileInput
from uuid import UUID
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.schemas.file import FileCreate, FileOut
from app.services import file_service
from app.db.session import get_db


DbSession = Annotated[Session, Depends(get_db)]


router = APIRouter(
    prefix="/files",
    tags=["Files"]
)


@router.get("/{file_id}", response_model=FileOut)
def get_file(file_id: UUID, db: DbSession):
    file = file_service.get_file(db, file_id)

    if file is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )

    return file


@router.get("/", response_model=list[FileOut])
def get_files(db: DbSession):
    return file_service.get_files(db)


@router.post("/", response_model=FileOut)
def upload_file(file_data: FileCreate, db: DbSession):
    return file_service.create_file(
        db,
        original_filename=file_data.original_filename,
        content_type=file_data.content_type
    )


@router.patch("/")
def update_file():
    pass


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_file(file_id: UUID, db: DbSession):
    deleted = file_service.delete_file(file_id, db)

    if not deleted:
        raise HTTPException(
            status=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )

