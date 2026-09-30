from pathlib import Path
from typing import BinaryIO
from uuid import uuid4

from app.core.config import settings
from app.core.exceptions import FileSizeExceededError

STORAGE_DIR = Path("storage/files")
CHUNK_SIZE = 1024 * 1024


class LocalStorageBackend:
    def __init__(
        self,
        *,
        storage_dir: Path = STORAGE_DIR,
        max_file_size: int | None = None,
    ) -> None:
        self._storage_dir = storage_dir
        self.max_file_size = (
            max_file_size
            if max_file_size is not None
            else settings.max_file_size_bytes
        )

    def generate_key(self, filename: str) -> str:
        extension = filename.rsplit(".", 1)[-1] if "." in filename else "bin"
        return f"{uuid4()}.{extension}"

    def save(self, file: BinaryIO, storage_key: str) -> int:
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        file_path = self._path(storage_key)
        total = 0

        try:
            with file_path.open("wb") as destination:
                while chunk := file.read(CHUNK_SIZE):
                    total += len(chunk)
                    if total > self.max_file_size:
                        raise FileSizeExceededError()
                    destination.write(chunk)
        except FileSizeExceededError:
            file_path.unlink(missing_ok=True)
            raise

        return total

    def read(self, storage_key: str) -> BinaryIO:
        return self._path(storage_key).open("rb")

    def delete(self, storage_key: str) -> None:
        file_path = self._path(storage_key)
        if file_path.is_file():
            file_path.unlink()

    def exists(self, storage_key: str) -> bool:
        return self._path(storage_key).is_file()

    def _path(self, storage_key: str) -> Path:
        return self._storage_dir / storage_key
