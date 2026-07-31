from datetime import datetime

from pydantic import BaseModel, ConfigDict


class StorageCleanupFailureRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    storage_path: str
    error_message: str
    status: str
    retry_count: int
    last_attempt_at: datetime | None
    created_at: datetime | None
    resolved_at: datetime | None


class StorageCleanupRetryRead(BaseModel):
    id: int
    resolved: bool
