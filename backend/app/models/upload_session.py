from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.file_status import FileStatus


class UploadSession(Base):
    __tablename__ = "upload_sessions"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    original_filename: Mapped[str] = mapped_column(String(255))

    content_type: Mapped[str] = mapped_column(String(100))

    expected_size: Mapped[int | None] = mapped_column(nullable=True)

    storage_key: Mapped[str] = mapped_column(String(500), unique=True)

    status: Mapped[FileStatus] = mapped_column(
        Enum(FileStatus, native_enum=False, length=50),
        default=FileStatus.PENDING,
    )

    bytes_received: Mapped[int] = mapped_column(default=0)

    file_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("files.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )
