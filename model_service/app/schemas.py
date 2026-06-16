from typing import Any, Literal

from pydantic import BaseModel


class AnalysisRequest(BaseModel):
    task_id: int
    video_path: str
    video_url: str
    metadata: dict[str, Any]


class AnalysisResponse(BaseModel):
    schema_version: str = "swim-analysis.v1"
    status: Literal["completed", "failed"] = "completed"
    detections: list[dict[str, Any]] = []
    keypoint_frames: list[dict[str, Any]] = []
    phases: list[dict[str, Any]] = []
    metrics: dict[str, Any] = {}
    diagnostics: list[dict[str, Any]] = []
    error_message: str | None = None
