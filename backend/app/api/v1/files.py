from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.file import FileOut
from app.services import file_service

DbSession = Annotated[Session, Depends(get_db)]


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
def get_files(db: DbSession):
    return file_service.get_files(db)


@router.post("/", response_model=FileOut)
def upload_file(uploaded_file: UploadFile, db: DbSession):
    return file_service.create_file(db, uploaded_file)


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
