from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional


class FileBase(BaseModel):
    original_filename: str
    content_type: str

class FileCreate(FileBase):
    pass

class FileUpdate(BaseModel):
    original_filename: str
    status: Optional[str] = None

class FileOut(FileBase):
    id: UUID
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)