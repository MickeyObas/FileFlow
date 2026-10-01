from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.job_status import JobStatus


class ProcessingJob(Base):
    __tablename__ = "processing_jobs"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    file_id: Mapped[UUID] = mapped_column(
        ForeignKey("files.id", ondelete="CASCADE"),
        unique=True,
    )

    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, native_enum=False, length=50),
        default=JobStatus.PENDING,
    )

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    result_payload: Mapped[str | None] = mapped_column(Text, nullable=True)

    result_storage_key: Mapped[str | None] = mapped_column(String(500), nullable=True)

    retry_count: Mapped[int] = mapped_column(Integer, default=0)

    stage: Mapped[str | None] = mapped_column(String(100), nullable=True)

    progress_percent: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
