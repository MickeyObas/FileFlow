from fileinput import filename
from fastapi import UploadFile
from sqlalchemy.orm import Session
from uuid import UUID

from app.models.file import File
from app.storage.local import MAX_FILE_SIZE, generate_storage_key, save_file


def get_file(db: Session, file_id: UUID) -> File | None:
    return db.get(File, file_id)

def get_files(db: Session) -> list[File]:
    return (
        db.query(File)
        .order_by(File.created_at.desc())
        .all()
    )

def create_file(db: Session, uploaded_file: UploadFile):
    filename = uploaded_file.filename
    content_type = uploaded_file.content_type
    file_size = uploaded_file.size


    validate_file(
        filename=filename,
        content_type=content_type,
        file_size=file_size
    )

    storage_key = generate_storage_key(filename)

    save_file(uploaded_file.file, storage_key)

    file = File(
        original_filename=uploaded_file.filename,
        content_type=uploaded_file.content_type,
        size=uploaded_file.size,
        storage_key=storage_key
    )

    db.add(file)
    db.commit()
    db.refresh(file)

    return file

def delete_file(db: Session, *, file_id: UUID) -> bool:
    file = get_file(db, file_id=file_id)

    if file is None:
        return False

    db.delete(file)
    db.commit()

    return True


ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "text/csv",
}


def validate_file(*, filename: str, content_type: str, file_size: str) -> None:
    if not filename:
        return ValueError("Filename is required")

    if content_type not in ALLOWED_CONTENT_TYPES:
        return ValueError("Unsupported file type")

    if file_size > MAX_FILE_SIZE:
        return ValueError("File exceeds maximum allowed size")

