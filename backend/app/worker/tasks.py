import json
from datetime import datetime
from io import BytesIO
from uuid import UUID

from rq import get_current_job

from app.db.session import SessionLocal
from app.models.file import File
from app.models.file_status import FileStatus
from app.models.job_status import JobStatus
from app.models.processing_job import ProcessingJob
from app.storage import get_storage_backend


def process_file_job(processing_job_id: str) -> None:
    db = SessionLocal()
    try:
        _run_processing(db, UUID(processing_job_id))
    except Exception as exc:
        rq_job = get_current_job()
        is_final_attempt = rq_job is None or rq_job.retries_left == 0
        if is_final_attempt:
            _mark_job_failed(db, UUID(processing_job_id), str(exc))
        raise
    finally:
        db.close()


def _run_processing(db, processing_job_id: UUID) -> None:
    job = _claim_job(db, processing_job_id)
    if job is None:
        return

    file = db.get(File, job.file_id)
    if file is None:
        raise RuntimeError(f"File {job.file_id} not found for job {processing_job_id}")

    storage = get_storage_backend()
    with storage.read(file.storage_key) as stream:
        raw = stream.read()

    result = {
        "byte_size": len(raw),
        "content_type": file.content_type,
        "original_filename": file.original_filename,
    }
    if file.content_type == "text/csv":
        try:
            text = raw.decode("utf-8")
            result["line_count"] = len(text.splitlines())
        except UnicodeDecodeError:
            result["line_count"] = None

    payload = json.dumps(result)
    result_key = storage.generate_key(f"result-{file.id}.json")
    storage.save(BytesIO(payload.encode("utf-8")), result_key)

    now = datetime.utcnow()
    job.status = JobStatus.COMPLETED
    job.error_message = None
    job.result_payload = payload
    job.result_storage_key = result_key
    job.completed_at = now
    job.updated_at = now

    file.status = FileStatus.COMPLETED
    db.commit()


def _claim_job(db, processing_job_id: UUID) -> ProcessingJob | None:
    job = (
        db.query(ProcessingJob)
        .filter(ProcessingJob.id == processing_job_id)
        .with_for_update()
        .one_or_none()
    )
    if job is None:
        return None

    if job.status in {JobStatus.COMPLETED, JobStatus.FAILED}:
        return None

    now = datetime.utcnow()
    file = db.get(File, job.file_id)

    if job.status == JobStatus.PENDING:
        job.status = JobStatus.PROCESSING
        job.started_at = job.started_at or now
        job.retry_count += 1
        if file is not None:
            file.status = FileStatus.PROCESSING

    job.updated_at = now
    db.commit()
    db.refresh(job)
    return job


def _mark_job_failed(db, processing_job_id: UUID, message: str) -> None:
    try:
        job = (
            db.query(ProcessingJob)
            .filter(ProcessingJob.id == processing_job_id)
            .with_for_update()
            .one_or_none()
        )
        if job is None or job.status == JobStatus.COMPLETED:
            return

        now = datetime.utcnow()
        job.status = JobStatus.FAILED
        job.error_message = message[:2000]
        job.completed_at = now
        job.updated_at = now

        file = db.get(File, job.file_id)
        if file is not None:
            file.status = FileStatus.FAILED

        db.commit()
    except Exception:
        db.rollback()
        raise
