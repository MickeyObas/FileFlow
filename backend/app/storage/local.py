from pathlib import Path
from typing import BinaryIO
from uuid import uuid4

from app.core.exceptions import FileSizeExceededError

MAX_FILE_SIZE = 50 * 1024 * 1024
STORAGE_DIR = Path("storage/files")
CHUNK_SIZE = 1024 * 1024


def generate_storage_key(filename: str) -> str:
    extension = filename.rsplit(".", 1)[-1] if "." in filename else "bin"
    return f"{uuid4()}.{extension}"


def save_file(file: BinaryIO, storage_key: str) -> int:
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    file_path = STORAGE_DIR / storage_key
    total = 0

    try:
        with file_path.open("wb") as destination:
            while chunk := file.read(CHUNK_SIZE):
                total += len(chunk)
                if total > MAX_FILE_SIZE:
                    raise FileSizeExceededError()
                destination.write(chunk)
    except FileSizeExceededError:
        file_path.unlink(missing_ok=True)
        raise

    return total


def delete_object(storage_key: str) -> None:
    file_path = STORAGE_DIR / storage_key
    if file_path.is_file():
        file_path.unlink()
