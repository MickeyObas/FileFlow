from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

StorageBackendName = Literal["local"]


class Settings(BaseSettings):
    database_url: str
    storage_backend: StorageBackendName = "local"
    max_file_size_bytes: int = 50 * 1024 * 1024
    redis_url: str = "redis://redis:6379/0"
    job_max_retries: int = 3
    job_retry_intervals: list[int] = [10, 30, 60]

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
