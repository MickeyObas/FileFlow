from collections.abc import Sequence
from contextlib import AbstractContextManager
from typing import BinaryIO, Protocol


class StorageWriter(Protocol):
    bytes_written: int

    def write(self, data: bytes) -> None: ...


class StorageBackend(Protocol):
    max_file_size: int

    def generate_key(self, filename: str) -> str: ...

    def save(self, file: BinaryIO, storage_key: str) -> int: ...

    def open_write(
        self,
        storage_key: str,
        *,
        part_number: int | None = None,
        max_bytes: int | None = None,
    ) -> AbstractContextManager[StorageWriter]: ...

    def assemble_parts(
        self,
        storage_key: str,
        part_numbers: Sequence[int],
    ) -> int: ...

    def list_parts(self, storage_key: str) -> list[int]: ...

    def part_size(self, storage_key: str, part_number: int) -> int | None: ...

    def delete_parts(self, storage_key: str) -> None: ...

    def size(self, storage_key: str) -> int | None: ...

    def read(self, storage_key: str) -> BinaryIO: ...

    def delete(self, storage_key: str) -> None: ...

    def exists(self, storage_key: str) -> bool: ...
