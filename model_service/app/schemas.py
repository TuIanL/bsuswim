from typing import Any, Literal

from pydantic import BaseModel


class VideoInput(BaseModel):
    video_file_id: int
    view_type: str
    video_url: str
    video_path: str
    fps: float | None = None
    resolution: str | None = None
    sync_offset_ms: int = 0


class AthleteInput(BaseModel):
    id: int
    name: str
    gender: str | None = None
    level: str | None = None


class SessionInput(BaseModel):
    id: int
    title: str
    stroke_type: str
    distance_m: int | None = None
    pool_length_m: float | None = None
    session_date: str | None = None


class AnalysisRequest(BaseModel):
    task_id: int
    session_id: int
    athlete: AthleteInput
    session: SessionInput
    videos: list[VideoInput]
    callback_url: str | None = None
    schema_version: str = "analysis.request.v1"


class AnalysisResponse(BaseModel):
    schema_version: str = "swim-analysis.v1"
    status: Literal["completed", "failed"] = "completed"
    detections: list[dict[str, Any]] = []
    keypoint_frames: list[dict[str, Any]] = []
    phases: list[dict[str, Any]] = []
    metrics: dict[str, Any] = {}
    diagnostics: list[dict[str, Any]] = []
    error_message: str | None = None
