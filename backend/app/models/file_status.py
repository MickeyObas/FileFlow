from enum import StrEnum


class FileStatus(StrEnum):
    """Lifecycle states used across uploads, files, and processing."""

    PENDING = "pending"
    UPLOADING = "uploading"
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"
