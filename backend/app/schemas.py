from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models import AnalysisTaskStatus


class TrainingMetadata(BaseModel):
    session_title: str = Field(min_length=1, max_length=120)
    venue: str | None = Field(default=None, max_length=120)
    session_date: str | None = None
    swimmer_label: str | None = Field(default=None, max_length=80)
    stroke_type: str = Field(default="freestyle", max_length=40)
    level: str | None = Field(default=None, max_length=40)
    capture_mode: str = Field(default="side_view", max_length=40)


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


class AnalysisTaskCreate(BaseModel):
    video_id: int
    metadata: TrainingMetadata


class AnalysisTaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    video_id: int
    status: AnalysisTaskStatus
    progress: int
    stage: str
    session_metadata: dict[str, Any]
    error_message: str | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    video: VideoFileRead | None = None
    actions: list[str] = []


class ModelAnalysisRequest(BaseModel):
    task_id: int
    video_path: str
    video_url: str
    metadata: dict[str, Any]


class ModelAnalysisResult(BaseModel):
    schema_version: str
    status: Literal["completed", "failed"] = "completed"
    detections: list[dict[str, Any]] = []
    keypoint_frames: list[dict[str, Any]] = []
    phases: list[dict[str, Any]] = []
    metrics: dict[str, Any] = {}
    diagnostics: list[dict[str, Any]] = []
    error_message: str | None = None


class AnalysisResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    schema_version: str
    detections: list[dict[str, Any]]
    keypoint_frames: list[dict[str, Any]]
    phases: list[dict[str, Any]]
    metrics: dict[str, Any]
    diagnostics: list[dict[str, Any]]
    created_at: datetime


class WorkspaceData(BaseModel):
    task: AnalysisTaskRead
    result: AnalysisResultRead | None


class ReportData(BaseModel):
    task_id: int
    source: str
    generated_at: datetime
    report: dict[str, Any]
