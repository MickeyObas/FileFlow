from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Path, Request, status
from sqlalchemy.orm import Session

from app.core.exceptions import FileSizeExceededError
from app.db.session import get_db
from app.schemas.file import FileDetailOut
from app.schemas.upload import UploadCreate, UploadOut
from app.services import idempotency_service, upload_service
from app.storage import get_storage_backend
from app.storage.protocol import StorageWriter

DbSession = Annotated[Session, Depends(get_db)]
IdempotencyKeyHeader = Annotated[str | None, Header(alias="Idempotency-Key")]


router = APIRouter(
    prefix="/uploads",
    tags=["Uploads"],
)


@router.post("/", response_model=UploadOut, status_code=status.HTTP_201_CREATED)
def create_upload(
    body: UploadCreate,
    db: DbSession,
    idempotency_key: IdempotencyKeyHeader = None,
):
    session = upload_service.create_upload(
        db,
        original_filename=body.original_filename,
        content_type=body.content_type,
        expected_size=body.expected_size,
        idempotency_key=idempotency_service.normalize_key(idempotency_key),
    )
    return UploadOut.from_session(session)


@router.get("/{upload_id}", response_model=UploadOut)
def get_upload(upload_id: UUID, db: DbSession):
    session = upload_service.get_upload(db, upload_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upload not found",
        )
    return UploadOut.from_session(session)


@router.put("/{upload_id}", response_model=UploadOut)
async def upload_body(upload_id: UUID, request: Request, db: DbSession):
    storage = get_storage_backend()
    session = upload_service.prepare_body_write(db, upload_id)
    _reject_oversized_content_length(request, storage.max_file_size)

    try:
        with storage.open_write(session.storage_key) as writer:
            await _stream_request(request, writer)
            bytes_written = writer.bytes_written
    except FileSizeExceededError as exc:
        raise _file_too_large() from exc

    session = upload_service.record_body_write(db, session, bytes_written)
    return UploadOut.from_session(session)


@router.put("/{upload_id}/parts/{part_number}", response_model=UploadOut)
async def upload_part(
    upload_id: UUID,
    part_number: Annotated[
        int,
        Path(ge=1, le=upload_service.MAX_PART_NUMBER),
    ],
    request: Request,
    db: DbSession,
):
    storage = get_storage_backend()
    session, previous_size = upload_service.prepare_part_write(
        db, upload_id, part_number
    )
    max_bytes = upload_service.remaining_bytes(
        session,
        storage,
        replacing=previous_size,
    )
    _reject_oversized_content_length(request, max_bytes)

    try:
        with storage.open_write(
            session.storage_key,
            part_number=part_number,
            max_bytes=max_bytes,
        ) as writer:
            await _stream_request(request, writer)
            bytes_written = writer.bytes_written
    except FileSizeExceededError as exc:
        raise _file_too_large() from exc

    session = upload_service.record_part_write(
        db,
        session,
        previous_size=previous_size,
        bytes_written=bytes_written,
    )
    return UploadOut.from_session(session)


@router.post("/{upload_id}/complete", response_model=FileDetailOut)
def complete_upload(
    upload_id: UUID,
    db: DbSession,
    idempotency_key: IdempotencyKeyHeader = None,
):
    from app.services import file_service

    file = upload_service.complete_upload(
        db,
        upload_id,
        idempotency_key=idempotency_service.normalize_key(idempotency_key),
    )
    row = file_service.get_file_with_job(db, file.id)
    assert row is not None
    file, job = row
    return FileDetailOut.from_file(file, processing_job=job)


async def _stream_request(request: Request, writer: StorageWriter) -> None:
    async for chunk in request.stream():
        writer.write(chunk)


def _reject_oversized_content_length(request: Request, max_bytes: int) -> None:
    content_length = request.headers.get("content-length")
    if content_length is None:
        return
    try:
        declared_size = int(content_length)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Content-Length header",
        )
    if declared_size > max_bytes:
        raise _file_too_large()


def _file_too_large() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_413_CONTENT_TOO_LARGE,
        detail="File exceeds maximum allowed size",
    )
