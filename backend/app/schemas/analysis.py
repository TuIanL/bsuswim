from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from app.models import AnalysisTaskStatus, StrokeType
from app.schemas.video import SessionVideoRead, VideoFileRead


class AnalysisSubmit(BaseModel):
    session_id: int
    normalized_annotation_id: int | None = None
    acknowledge_quality_warnings: bool = False


class AnalysisTaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    status: AnalysisTaskStatus
    progress: int
    stage: str
    request_payload: dict[str, Any]
    error_message: str | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    actions: list[str] = []


class AnalysisStatusRead(BaseModel):
    task_id: int
    session_id: int
    status: AnalysisTaskStatus
    progress: int
    stage: str
    error_message: str | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None


class ModelVideoInput(BaseModel):
    video_file_id: int
    view_type: str
    video_url: str
    video_path: str
    fps: float | None = None
    resolution: str | None = None
    sync_offset_ms: int = 0


class ModelAthleteInput(BaseModel):
    id: int
    name: str
    gender: str | None = None
    level: str | None = None


class ModelSessionInput(BaseModel):
    id: int
    title: str
    stroke_type: StrokeType
    distance_m: int | None = None
    pool_length_m: float | None = None
    session_date: date | None = None


class ModelAnalysisRequest(BaseModel):
    task_id: int
    session_id: int
    athlete: ModelAthleteInput
    session: ModelSessionInput
    videos: list[ModelVideoInput]
    callback_url: str | None = None
    schema_version: str = "analysis.request.v1"


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
    quality_summary: dict[str, Any] = {}
    created_at: datetime


class WorkspaceData(BaseModel):
    task: AnalysisTaskRead
    result: AnalysisResultRead | None
    videos: list[VideoFileRead] = []
    session_videos: list[SessionVideoRead] = []
