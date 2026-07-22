from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models import ViewType


class VideoFileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    original_filename: str
    stored_filename: str
    storage_path: str
    mime_type: str | None
    size_bytes: int
    checksum_sha256: str
    created_at: datetime
    playback_url: str


class VideoUploadResponse(BaseModel):
    video: VideoFileRead
    probed_fps: float | None = None
    resolution: str | None = Field(default=None, max_length=40)
    metadata_source: str | None = None
    fps_verified: bool = False


class SessionVideoCreate(BaseModel):
    video_file_id: int
    view_type: ViewType = ViewType.SIDE
    fps: float | None = None
    resolution: str | None = Field(default=None, max_length=40)
    sync_offset_ms: int = 0


class SessionVideoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    video_file_id: int
    view_type: ViewType
    fps: float | None
    resolution: str | None
    sync_offset_ms: int
    created_at: datetime
    video: VideoFileRead
