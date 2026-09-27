from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class File(Base):
    __tablename__ = "files"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )

    original_filename: Mapped[str] = mapped_column(String(255))

    storage_key: Mapped[str] = mapped_column(String(500), unique=True)

    content_type: Mapped[str] = mapped_column(String(100))

    size: Mapped[int] = mapped_column()

    status: Mapped[str] = mapped_column(
        String(50),
        default="uploaded",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )