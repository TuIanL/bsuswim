from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.annotation import AnnotationSource, AnnotationFileStatus
from app.models.video import ViewType


# ── V1 Quality (legacy, keep for backward compat) ──


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


# ── V2 Quality schemas ──


class AnalysisReadiness(BaseModel):
    can_submit: bool = False
    requires_acknowledgement: bool = False
    blocking_issue_count: int = 0
    affected_modules: list[str] = Field(default_factory=list)


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
    x: float | None = None
    y: float | None = None
    confidence: float | None = None
    visibility: Literal["visible", "occluded", "estimated", "missing"] = "visible"

    @model_validator(mode="after")
    def validate_coordinate_visibility(self):
        if self.visibility == "missing":
            if self.x is not None or self.y is not None:
                raise ValueError("missing point must not contain coordinates")
        else:
            if self.x is None or self.y is None:
                raise ValueError(
                    "visible, occluded or estimated point requires coordinates"
                )
        return self


class KeypointFrame(BaseModel):
    frame: int
    time_sec: float
    phase: str = ""
    points: dict[str, KeypointPoint] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    annotation_frame: int | None = None
    source_video_frame: int | None = None
    timestamp_sec: float | None = None
    image_name: str | None = None


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


# ── Frame mapping schemas ──


class FrameMappingEntry(BaseModel):
    annotation_frame: int
    source_video_frame: int | None = None
    timestamp_sec: float | None = None
    image_name: str | None = None


class FrameMapping(BaseModel):
    mode: Literal["explicit", "affine", "identity", "unknown"] = "unknown"
    verified: bool = False
    verification_reason: str | None = None
    source_frame_offset: int | None = None
    source_frame_stride: int | None = None
    video_fps: float | None = None
    entries: list[FrameMappingEntry] | None = None


class AnalysisRange(BaseModel):
    start_annotation_frame: int
    end_annotation_frame: int
    purpose: str = ""
    source: str = "manual"


class FrameMappingOverride(BaseModel):
    mode: Literal["affine", "identity"]
    source_frame_offset: int | None = None
    source_frame_stride: int | None = None
    confirmed: bool = False


class ParseAnnotationOptions(BaseModel):
    companion_annotation_file_id: int | None = None
    frame_mapping_override: FrameMappingOverride | None = None
    analysis_ranges: list[AnalysisRange] = []


# ── CVAT raw data schemas ──


class RawCvatPoint(BaseModel):
    x: float
    y: float
    visibility: Literal["visible", "occluded", "missing"]


class RawCvatKeypointFrame(BaseModel):
    annotation_frame: int
    points: dict[str, RawCvatPoint] = Field(default_factory=dict)
    source_track_ids: list[str] = Field(default_factory=list)


class ParsedCvatAnnotation(BaseModel):
    raw_keypoint_frames: list[RawCvatKeypointFrame] = Field(default_factory=list)
    native_metadata: dict = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


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
    reference_lines: dict | None = None
    distance_markers: list[dict] | None = None
    swim_direction: str | None = None


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
    reference_lines: dict | None = None
    distance_markers: list | None = None
    swim_direction: str | None = None
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


class ParseSummary(BaseModel):
    """解析结果计数摘要（events / keypoint_frames / trajectories / manual_tags 数量）。"""

    events_count: int = 0
    keypoint_frames_count: int = 0
    trajectories_count: int = 0
    manual_tags_count: int = 0


class ParseResponse(BaseModel):
    """parse endpoint 响应。"""

    normalized_annotation_id: int
    annotation_file_id: int
    source: AnnotationSource
    status: AnnotationFileStatus
    schema_version: str
    revision: int
    summary: ParseSummary
    quality: AnnotationQuality
    analysis_readiness: AnalysisReadiness | None = None
    warnings: list[str] = Field(default_factory=list)
