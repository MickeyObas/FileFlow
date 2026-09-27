from sqlalchemy.orm import Session
from uuid import UUID

from app.models.file import File


def get_file(db: Session, file_id: UUID) -> File | None:
    return db.get(File, file_id)

def get_files(db: Session) -> list[File]:
    return (
        db.query(File)
        .order_by(File.created_at.desc())
        .all()
    )

def create_file(db: Session, *, original_filename: str, content_type: str):
    file = File(
        original_filename=original_filename,
        content_type=content_type
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