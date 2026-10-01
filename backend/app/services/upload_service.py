from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.exceptions import FileSizeExceededError
from app.models.file import File
from app.models.file_status import FileStatus
from app.models.upload_session import UploadSession
from app.services import idempotency_service
from app.services.file_service import validate_file
from app.storage import get_storage_backend
from app.storage.protocol import StorageBackend

MAX_PART_NUMBER = 10_000
OPEN_STATUSES = {FileStatus.PENDING, FileStatus.UPLOADING}


def get_upload(db: Session, upload_id: UUID) -> UploadSession | None:
    return db.get(UploadSession, upload_id)


def create_upload(
    db: Session,
    *,
    original_filename: str,
    content_type: str,
    expected_size: int | None,
    idempotency_key: str | None = None,
) -> UploadSession:
    storage = get_storage_backend()
    validate_file(
        filename=original_filename,
        content_type=content_type,
        file_size=expected_size,
        max_file_size=storage.max_file_size,
    )

    request_fingerprint = idempotency_service.fingerprint_upload_create(
        original_filename=original_filename,
        content_type=content_type,
        expected_size=expected_size,
    )
    if idempotency_key is not None:
        replay_id = idempotency_service.replay_resource_id(
            db,
            key=idempotency_key,
            operation=idempotency_service.UPLOAD_CREATE,
            request_fingerprint=request_fingerprint,
        )
        if replay_id is not None:
            session = get_upload(db, replay_id)
            if session is not None:
                return session

    session = UploadSession(
        original_filename=original_filename,
        content_type=content_type,
        expected_size=expected_size,
        storage_key=storage.generate_key(original_filename),
        status=FileStatus.PENDING,
        bytes_received=0,
    )
    db.add(session)
    db.flush()

    if idempotency_key is not None:
        idempotency_service.attach_record(
            db,
            key=idempotency_key,
            operation=idempotency_service.UPLOAD_CREATE,
            resource_id=session.id,
            request_fingerprint=request_fingerprint,
        )

    if idempotency_key is not None:
        replay_id = idempotency_service.commit_or_replay_resource_id(
            db,
            key=idempotency_key,
            operation=idempotency_service.UPLOAD_CREATE,
            request_fingerprint=request_fingerprint,
        )
        if replay_id is not None:
            session = get_upload(db, replay_id)
            if session is None:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Idempotent upload session is missing",
                )
            return session
    else:
        db.commit()

    db.refresh(session)
    return session


def prepare_body_write(db: Session, upload_id: UUID) -> UploadSession:
    storage = get_storage_backend()
    session = _get_writable_session(db, upload_id)
    if storage.list_parts(session.storage_key):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Upload already has parts; send additional parts instead",
        )
    return session


def prepare_part_write(
    db: Session,
    upload_id: UUID,
    part_number: int,
) -> tuple[UploadSession, int]:
    if part_number < 1 or part_number > MAX_PART_NUMBER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Part number must be between 1 and {MAX_PART_NUMBER}",
        )

    storage = get_storage_backend()
    session = _get_writable_session(db, upload_id)
    if storage.exists(session.storage_key):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Upload already has a full body; use PUT on the upload instead",
        )

    previous_size = storage.part_size(session.storage_key, part_number) or 0
    return session, previous_size


def remaining_bytes(
    session: UploadSession,
    storage: StorageBackend,
    *,
    replacing: int = 0,
) -> int:
    used = max(session.bytes_received - replacing, 0)
    return max(storage.max_file_size - used, 0)


def record_body_write(
    db: Session,
    session: UploadSession,
    bytes_written: int,
) -> UploadSession:
    if bytes_written == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload body is empty",
        )
    session.bytes_received = bytes_written
    session.status = FileStatus.UPLOADING
    db.commit()
    db.refresh(session)
    return session


def record_part_write(
    db: Session,
    session: UploadSession,
    *,
    previous_size: int,
    bytes_written: int,
) -> UploadSession:
    if bytes_written == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload part is empty",
        )
    session.bytes_received = session.bytes_received - previous_size + bytes_written
    session.status = FileStatus.UPLOADING
    db.commit()
    db.refresh(session)
    return session


def complete_upload(
    db: Session,
    upload_id: UUID,
    *,
    idempotency_key: str | None = None,
) -> File:
    storage = get_storage_backend()
    request_fingerprint = idempotency_service.fingerprint_upload_complete(
        upload_id=upload_id,
    )
    if idempotency_key is not None:
        replay_id = idempotency_service.replay_resource_id(
            db,
            key=idempotency_key,
            operation=idempotency_service.UPLOAD_COMPLETE,
            request_fingerprint=request_fingerprint,
        )
        if replay_id is not None:
            file = db.get(File, replay_id)
            if file is not None:
                return file

    session = _get_session_for_update(db, upload_id)

    if session.status == FileStatus.COMPLETED and session.file_id is not None:
        file = db.get(File, session.file_id)
        if file is not None:
            _store_complete_idempotency(
                db,
                idempotency_key=idempotency_key,
                request_fingerprint=request_fingerprint,
                file_id=file.id,
            )
            return file

    if session.status not in OPEN_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Upload cannot be completed in status {session.status}",
        )

    try:
        actual_size = _finalize_storage(storage, session)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except FileSizeExceededError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="File exceeds maximum allowed size",
        ) from exc

    if actual_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No upload data received",
        )

    if session.expected_size is not None and actual_size != session.expected_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded size does not match expected_size",
        )

    file = File(
        original_filename=session.original_filename,
        content_type=session.content_type,
        size=actual_size,
        storage_key=session.storage_key,
        status=FileStatus.UPLOADED,
    )
    db.add(file)
    db.flush()

    session.status = FileStatus.COMPLETED
    session.bytes_received = actual_size
    session.file_id = file.id

    if idempotency_key is not None:
        idempotency_service.attach_record(
            db,
            key=idempotency_key,
            operation=idempotency_service.UPLOAD_COMPLETE,
            resource_id=file.id,
            request_fingerprint=request_fingerprint,
        )

    if idempotency_key is not None:
        replay_id = idempotency_service.commit_or_replay_resource_id(
            db,
            key=idempotency_key,
            operation=idempotency_service.UPLOAD_COMPLETE,
            request_fingerprint=request_fingerprint,
        )
        if replay_id is not None:
            file = db.get(File, replay_id)
            if file is None:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Idempotent completed file is missing",
                )
            return file
    else:
        db.commit()

    db.refresh(file)
    return file


def _finalize_storage(
    storage: StorageBackend,
    session: UploadSession,
) -> int:
    object_size = storage.size(session.storage_key)
    if object_size is not None:
        return object_size

    part_numbers = storage.list_parts(session.storage_key)
    if not part_numbers:
        return 0

    expected_parts = list(range(1, len(part_numbers) + 1))
    if part_numbers != expected_parts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload parts must be contiguous starting at 1",
        )

    return storage.assemble_parts(session.storage_key, part_numbers)


def _get_writable_session(db: Session, upload_id: UUID) -> UploadSession:
    session = _get_session_or_404(db, upload_id)
    if session.status not in OPEN_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Upload cannot accept data in status {session.status}",
        )
    return session


def _get_session_or_404(db: Session, upload_id: UUID) -> UploadSession:
    session = get_upload(db, upload_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upload not found",
        )
    return session


def _get_session_for_update(db: Session, upload_id: UUID) -> UploadSession:
    session = (
        db.query(UploadSession)
        .filter(UploadSession.id == upload_id)
        .with_for_update()
        .one_or_none()
    )
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upload not found",
        )
    return session


def _store_complete_idempotency(
    db: Session,
    *,
    idempotency_key: str | None,
    request_fingerprint: str,
    file_id: UUID,
) -> None:
    if idempotency_key is None:
        return
    existing = idempotency_service.find_record(db, idempotency_key)
    if existing is not None:
        return
    idempotency_service.attach_record(
        db,
        key=idempotency_key,
        operation=idempotency_service.UPLOAD_COMPLETE,
        resource_id=file_id,
        request_fingerprint=request_fingerprint,
    )
    idempotency_service.commit_or_replay_resource_id(
        db,
        key=idempotency_key,
        operation=idempotency_service.UPLOAD_COMPLETE,
        request_fingerprint=request_fingerprint,
    )
