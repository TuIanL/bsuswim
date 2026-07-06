from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.annotation import AnnotationSource, AnnotationFileStatus
from app.models.video import ViewType


# ── Quality ──


class QualityCheck(BaseModel):
    key: str
    status: Literal["passed", "warning", "failed"]
    message: str


class AnnotationQuality(BaseModel):
    level: Literal["good", "warning", "error"]
    score: int | None = None
    checks: list[QualityCheck] = Field(default_factory=list)
    usable_modules: list[str] = Field(default_factory=list)
    disabled_modules: list[dict[str, Any]] = Field(default_factory=list)

    model_config = ConfigDict(extra="allow")


# ── Sub-structures ──


class AnnotationEvent(BaseModel):
    name: str
    label: str
    frame: int
    time_sec: float
    side: Literal["left", "right", "both", "unknown"] = "unknown"
    confidence: float = 1.0
    labeled_by: Literal["manual", "kinovea", "ai", "derived", "unknown"] = "manual"


class KeypointPoint(BaseModel):
    x: float
    y: float
    confidence: float = 1.0
    visibility: Literal["visible", "occluded", "estimated", "missing"] = "visible"


class KeypointFrame(BaseModel):
    frame: int
    time_sec: float
    phase: str = ""
    points: dict[str, KeypointPoint] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)


class Trajectory(BaseModel):
    name: str
    label: str
    point: str
    frames: list[int] = Field(default_factory=list)
    points: list[list[float]] = Field(default_factory=list)
    source: str = "manual"


class ManualTag(BaseModel):
    code: str
    label: str
    severity: Literal["low", "medium", "high"] = "medium"
    phase: str = ""
    frame_range: list[int] = Field(default_factory=list)
    comment: str = ""


class ScaleInfo(BaseModel):
    method: Literal["lane_marker", "pool_wall_marker", "manual_reference"] = "lane_marker"
    pixels_per_meter: float | None = None
    reference_length_m: float | None = None
    reference_points: list[list[float]] = Field(default_factory=list)
    confidence: float | None = None
    note: str | None = None


class CoordinateSystem(BaseModel):
    origin: str = "top_left"
    x_axis: str = "right"
    y_axis: str = "down"
    unit: str = "pixel"


class VideoContext(BaseModel):
    fps: float
    frame_count: int | None = None
    duration_sec: float | None = None
    width: int | None = None
    height: int | None = None


# ── API schemas ──


class NormalizedAnnotationCreate(BaseModel):
    """创建标准化标注的请求 body。"""

    annotation_file_id: int | None = None
    source: AnnotationSource = AnnotationSource.MANUAL_JSON
    fps: float
    frame_count: int | None = None
    duration_sec: float | None = None
    scale: ScaleInfo | None = None
    coordinate_system: CoordinateSystem = Field(default_factory=CoordinateSystem)
    events: list[AnnotationEvent] = Field(default_factory=list)
    keypoint_frames: list[KeypointFrame] = Field(default_factory=list)
    trajectories: list[Trajectory] = Field(default_factory=list)
    manual_tags: list[ManualTag] = Field(default_factory=list)


class NormalizedAnnotationRead(BaseModel):
    """标准化标注完整响应。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    session_video_id: int
    session_id: int | None = None
    video_file_id: int | None = None
    view_type: ViewType | None = None
    annotation_file_id: int | None = None
    revision: int
    schema_version: str
    source: AnnotationSource
    fps: float
    frame_count: int | None
    duration_sec: float | None
    scale: dict | None
    coordinate_system: dict
    events: list
    keypoint_frames: list
    trajectories: list
    manual_tags: list
    quality: dict
    annotation_metadata: dict
    created_by: int | None
    created_at: datetime
    updated_at: datetime


class NormalizedAnnotationListItem(BaseModel):
    """标准化标注列表摘要。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    session_video_id: int
    annotation_file_id: int | None = None
    revision: int
    schema_version: str
    source: AnnotationSource
    view_type: ViewType | None = None
    quality_level: str | None = None
    created_at: datetime


class ParseResponse(BaseModel):
    """parse endpoint 响应。"""

    normalized_annotation_id: int
    status: AnnotationFileStatus
    schema_version: str
    revision: int
    quality: AnnotationQuality
