from uuid import UUID

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import FileSizeExceededError
from app.models.file import File
from app.models.file_status import FileStatus
from app.services import idempotency_service
from app.storage import get_storage_backend


def get_file(db: Session, file_id: UUID) -> File | None:
    return db.get(File, file_id)


def get_files(
    db: Session,
    status: FileStatus | None = None,
) -> list[File]:
    query = db.query(File)
    if status is not None:
        query = query.filter(File.status == status)
    return query.order_by(File.created_at.desc()).all()


def create_file(
    db: Session,
    uploaded_file: UploadFile,
    *,
    idempotency_key: str | None = None,
) -> File:
    storage = get_storage_backend()
    filename = uploaded_file.filename or ""
    content_type = uploaded_file.content_type or ""

    validate_file(
        filename=filename,
        content_type=content_type,
        file_size=uploaded_file.size,
        max_file_size=storage.max_file_size,
    )

    request_fingerprint = idempotency_service.fingerprint_file_create(
        filename=filename,
        content_type=content_type,
        file_size=uploaded_file.size,
    )
    if idempotency_key is not None:
        replay_id = idempotency_service.replay_resource_id(
            db,
            key=idempotency_key,
            operation=idempotency_service.FILE_CREATE,
            request_fingerprint=request_fingerprint,
        )
        if replay_id is not None:
            file = get_file(db, replay_id)
            if file is not None:
                return file

    storage_key = storage.generate_key(filename)

    try:
        actual_size = storage.save(uploaded_file.file, storage_key)
    except FileSizeExceededError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="File exceeds maximum allowed size",
        ) from exc

    file = File(
        original_filename=filename,
        content_type=content_type,
        size=actual_size,
        storage_key=storage_key,
        status=FileStatus.UPLOADED,
    )

    db.add(file)
    db.flush()

    if idempotency_key is not None:
        idempotency_service.attach_record(
            db,
            key=idempotency_key,
            operation=idempotency_service.FILE_CREATE,
            resource_id=file.id,
            request_fingerprint=request_fingerprint,
        )

    try:
        if idempotency_key is not None:
            replay_id = idempotency_service.commit_or_replay_resource_id(
                db,
                key=idempotency_key,
                operation=idempotency_service.FILE_CREATE,
                request_fingerprint=request_fingerprint,
            )
            if replay_id is not None:
                orphan = file
                file = get_file(db, replay_id)
                if file is None:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Idempotent file record is missing",
                    )
                storage.delete(orphan.storage_key)
                return file
        else:
            db.commit()
    except Exception:
        db.rollback()
        storage.delete(storage_key)
        raise

    db.refresh(file)
    return file


def delete_file(db: Session, *, file_id: UUID) -> bool:
    storage = get_storage_backend()
    file = get_file(db, file_id)

    if file is None:
        return False

    storage_key = file.storage_key
    db.delete(file)
    db.commit()
    storage.delete(storage_key)

    return True


ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "text/csv",
}


def validate_file(
    *,
    filename: str,
    content_type: str,
    file_size: int | None,
    max_file_size: int = settings.max_file_size_bytes,
) -> None:
    if not filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required",
        )

    if content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported file type",
        )

    if file_size is not None and file_size > max_file_size:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="File exceeds maximum allowed size",
        )
