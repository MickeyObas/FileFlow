from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import BinaryIO
from uuid import uuid4

from app.core.config import settings
from app.core.exceptions import FileSizeExceededError
from app.storage.protocol import StorageWriter

STORAGE_DIR = Path("storage/files")
CHUNK_SIZE = 1024 * 1024


class _StreamWriter:
    def __init__(self, path: Path, max_bytes: int) -> None:
        self._path = path
        self._max_bytes = max_bytes
        self.bytes_written = 0
        self._fh: BinaryIO | None = None

    def open(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = self._path.open("wb")

    def write(self, data: bytes) -> None:
        if not data:
            return
        if self._fh is None:
            raise RuntimeError("writer is not open")
        self.bytes_written += len(data)
        if self.bytes_written > self._max_bytes:
            raise FileSizeExceededError()
        self._fh.write(data)

    def close(self) -> None:
        if self._fh is not None:
            self._fh.close()
            self._fh = None

    def cleanup(self) -> None:
        self._path.unlink(missing_ok=True)


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
        with self.open_write(storage_key) as writer:
            while chunk := file.read(CHUNK_SIZE):
                writer.write(chunk)
            return writer.bytes_written

    @contextmanager
    def open_write(
        self,
        storage_key: str,
        *,
        part_number: int | None = None,
        max_bytes: int | None = None,
    ) -> Iterator[StorageWriter]:
        path = (
            self._part_path(storage_key, part_number)
            if part_number is not None
            else self._path(storage_key)
        )
        writer = _StreamWriter(
            path,
            self.max_file_size if max_bytes is None else max_bytes,
        )
        writer.open()
        try:
            yield writer
            writer.close()
        except Exception:
            writer.close()
            writer.cleanup()
            raise

    def assemble_parts(
        self,
        storage_key: str,
        part_numbers: Sequence[int],
    ) -> int:
        missing = [
            part_number
            for part_number in part_numbers
            if not self._part_path(storage_key, part_number).is_file()
        ]
        if missing:
            raise FileNotFoundError(f"Missing upload parts: {missing}")

        with self.open_write(storage_key) as writer:
            for part_number in part_numbers:
                part_path = self._part_path(storage_key, part_number)
                with part_path.open("rb") as part:
                    while chunk := part.read(CHUNK_SIZE):
                        writer.write(chunk)
            total = writer.bytes_written

        self.delete_parts(storage_key)
        return total

    def list_parts(self, storage_key: str) -> list[int]:
        parts_dir = self._parts_dir(storage_key)
        if not parts_dir.is_dir():
            return []

        part_numbers: list[int] = []
        for path in parts_dir.iterdir():
            if path.is_file() and path.name.isdigit():
                part_numbers.append(int(path.name))
        return sorted(part_numbers)

    def part_size(self, storage_key: str, part_number: int) -> int | None:
        path = self._part_path(storage_key, part_number)
        if not path.is_file():
            return None
        return path.stat().st_size

    def delete_parts(self, storage_key: str) -> None:
        parts_dir = self._parts_dir(storage_key)
        if not parts_dir.is_dir():
            return
        for path in parts_dir.iterdir():
            if path.is_file():
                path.unlink()
        parts_dir.rmdir()

    def read(self, storage_key: str) -> BinaryIO:
        return self._path(storage_key).open("rb")

    def delete(self, storage_key: str) -> None:
        file_path = self._path(storage_key)
        if file_path.is_file():
            file_path.unlink()
        self.delete_parts(storage_key)

    def size(self, storage_key: str) -> int | None:
        file_path = self._path(storage_key)
        if not file_path.is_file():
            return None
        return file_path.stat().st_size

    def exists(self, storage_key: str) -> bool:
        return self._path(storage_key).is_file()

    def _path(self, storage_key: str) -> Path:
        return self._storage_dir / storage_key

    def _parts_dir(self, storage_key: str) -> Path:
        return self._storage_dir / f"{storage_key}.parts"

    def _part_path(self, storage_key: str, part_number: int) -> Path:
        return self._parts_dir(storage_key) / f"{part_number:05d}"
