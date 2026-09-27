from uuid import uuid4
from pathlib import Path
from typing import BinaryIO

MAX_FILE_SIZE = 50 * 1024 * 1024
STORAGE_DIR = Path("storage/files")

def generate_storage_key(filename: str) -> str:
    extension = filename.split(".", 1)[-1]
    
    return f"{uuid4()}.{extension}"

def save_file(file: BinaryIO, storage_key: str):
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    file_path = STORAGE_DIR / storage_key

    with file_path.open("wb") as destination:
        while chunk := file.read(1024 * 1024):
            destination.write(chunk) 