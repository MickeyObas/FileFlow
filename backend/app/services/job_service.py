import logging
from uuid import UUID

from rq import Retry
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.job_status import JobStatus
from app.models.processing_job import ProcessingJob
from app.worker.queue import get_queue
from app.worker.tasks import process_file_job

logger = logging.getLogger(__name__)


def get_job(db: Session, job_id: UUID) -> ProcessingJob | None:
    return db.get(ProcessingJob, job_id)


def get_job_for_file(db: Session, file_id: UUID) -> ProcessingJob | None:
    return (
        db.query(ProcessingJob)
        .filter(ProcessingJob.file_id == file_id)
        .one_or_none()
    )


def ensure_pending_job(db: Session, file_id: UUID) -> ProcessingJob:
    existing = get_job_for_file(db, file_id)
    if existing is not None:
        return existing

    job = ProcessingJob(
        file_id=file_id,
        status=JobStatus.PENDING,
        retry_count=0,
    )
    db.add(job)
    db.flush()
    return job


def enqueue_processing_job(job_id: UUID) -> None:
    queue = get_queue()
    queue.enqueue(
        process_file_job,
        str(job_id),
        job_id=f"fileflow-process-{job_id}",
        retry=Retry(
            max=settings.job_max_retries,
            interval=settings.job_retry_intervals,
        ),
    )
    logger.info("Enqueued processing job %s", job_id)


def enqueue_if_pending(job: ProcessingJob) -> None:
    if job.status == JobStatus.PENDING:
        enqueue_processing_job(job.id)
