import hashlib
import json
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.idempotency_record import IdempotencyRecord

MAX_KEY_LENGTH = 255

UPLOAD_CREATE = "upload.create"
FILE_CREATE = "file.create"
UPLOAD_COMPLETE = "upload.complete"


def normalize_key(raw: str | None) -> str | None:
    if raw is None:
        return None
    key = raw.strip()
    if not key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Idempotency-Key must not be empty",
        )
    if len(key) > MAX_KEY_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Idempotency-Key must be at most {MAX_KEY_LENGTH} characters",
        )
    return key


def fingerprint_upload_create(
    *,
    original_filename: str,
    content_type: str,
    expected_size: int | None,
) -> str:
    payload = {
        "original_filename": original_filename,
        "content_type": content_type,
        "expected_size": expected_size,
    }
    return _hash_payload(payload)


def fingerprint_file_create(
    *,
    filename: str,
    content_type: str,
    file_size: int | None,
) -> str:
    payload = {
        "filename": filename,
        "content_type": content_type,
        "file_size": file_size,
    }
    return _hash_payload(payload)


def fingerprint_upload_complete(*, upload_id: UUID) -> str:
    return _hash_payload({"upload_id": str(upload_id)})


def find_record(db: Session, key: str) -> IdempotencyRecord | None:
    return db.get(IdempotencyRecord, key)


def replay_resource_id(
    db: Session,
    *,
    key: str,
    operation: str,
    request_fingerprint: str,
) -> UUID | None:
    record = find_record(db, key)
    if record is None:
        return None
    if record.operation != operation:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Idempotency-Key was already used for a different operation",
        )
    if record.request_fingerprint != request_fingerprint:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Idempotency-Key was already used with a different request",
        )
    return record.resource_id


def attach_record(
    db: Session,
    *,
    key: str,
    operation: str,
    resource_id: UUID,
    request_fingerprint: str,
) -> None:
    db.add(
        IdempotencyRecord(
            key=key,
            operation=operation,
            resource_id=resource_id,
            request_fingerprint=request_fingerprint,
        )
    )


def commit_or_replay_resource_id(
    db: Session,
    *,
    key: str,
    operation: str,
    request_fingerprint: str,
) -> UUID | None:
    try:
        db.commit()
        return None
    except IntegrityError:
        db.rollback()
        return replay_resource_id(
            db,
            key=key,
            operation=operation,
            request_fingerprint=request_fingerprint,
        )


def _hash_payload(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()
