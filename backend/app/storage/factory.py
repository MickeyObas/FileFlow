from typing import Literal

from app.core.config import settings
from app.storage.local import LocalStorageBackend
from app.storage.protocol import StorageBackend

StorageBackendName = Literal["local"]


def get_storage_backend() -> StorageBackend:
    backend = settings.storage_backend

    if backend == "local":
        return LocalStorageBackend()

    raise ValueError(f"Unsupported storage backend: {backend!r}")
