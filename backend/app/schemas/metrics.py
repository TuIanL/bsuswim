"""Side-view metrics output schemas.

这些 schema 仅描述**事实测量值**，不含任何诊断结论。Change #5（规则诊断）
与 Change #6（报告装配）读取本层产出的 metrics 后再各自生成结论。
"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


# ── 计算器与 schema 常量 ──

SCHEMA_SIDE_METRICS = "swim-side-metrics.v1"
CALCULATOR_SIDE_VIEW_METRICS = "side_view_metrics"
CALCULATOR_VERSION_SIDE_VIEW = "0.1.0"

SCHEMA_SIDE_2D_KINEMATICS = "swim-side-kinematics.v1"
CALCULATOR_SIDE_2D_KINEMATICS = "side_2d_kinematics"
CALCULATOR_VERSION_SIDE_2D = "1.0.0"

MetricCategory = Literal["body_posture", "upper_limb", "lower_limb", "head_trunk"]


class MetricValue(BaseModel):
    """单个核心指标的承载结构，附带单位、来源与质量，便于 report_builder 直接展示。"""

    key: str
    label: str
    value: float | int | None = None
    unit: str | None = None
    source: dict = Field(default_factory=dict)
    quality: dict = Field(default_factory=dict)


class MetricSeriesPoint(BaseModel):
    frame: int
    time_sec: float
    value: float | None = None


# ── 旧 side_view_metrics 输出结构（保持向后兼容）──


class SideViewMetrics(BaseModel):
    """side-view metrics 的固定输出结构，schema_version = swim-side-metrics.v1。"""

    model_config = ConfigDict(extra="allow")

    schema_version: str = SCHEMA_SIDE_METRICS
    camera_view: str = "side"
    calculator: str = CALCULATOR_SIDE_VIEW_METRICS
    calculator_version: str = CALCULATOR_VERSION_SIDE_VIEW
    summary: dict = Field(default_factory=dict)
    time_series: dict = Field(default_factory=dict)
    cycles: list[dict] = Field(default_factory=list)
    phase_metrics: list[dict] = Field(default_factory=list)
    quality: dict = Field(default_factory=dict)


# ── 新 side_2d_kinematics 输出结构 ──


class MetricProvenance(BaseModel):
    """指标来源帧区间与映射状态。"""

    annotation_frame_ranges: list[list[int]] = Field(default_factory=list)
    source_video_frame_ranges: list[list[int]] = Field(default_factory=list)
    frame_basis: Literal["annotation_frame", "source_video_frame"] = "annotation_frame"
    mapping_status: Literal["verified", "unverified", "unknown"] = "unknown"


class MetricEnvelope(BaseModel):
    """统一指标承载：值 + 单位 + 可用性 + 置信度 + 来源 + 参考基准。"""

    key: str
    category: MetricCategory
    value: float | int | list | dict | None = None
    unit: str | None = None
    sample_count: int = 0
    availability: Literal["available", "low_confidence", "unavailable"] = "unavailable"
    confidence: float = 0.0
    provenance: MetricProvenance = Field(default_factory=MetricProvenance)
    reference_basis: Literal[
        "screen_horizontal", "joint_geometry", "pixel", "normalized_body_length", "frame_sequence"
    ] = "screen_horizontal"
    details: dict = Field(default_factory=dict)


class MetricRange(BaseModel):
    """指标在序列上的取值范围。"""

    metric_key: str
    category: MetricCategory
    min: float | None = None
    max: float | None = None
    p05: float | None = None
    p95: float | None = None


class KinematicSeriesPoint(BaseModel):
    """逐帧运动学序列点。"""

    frame: int
    time_sec: float
    value: float | None = None
    annotation_frame: int | None = None
    source_video_frame: int | None = None
    confidence: float | None = None
    construction_mode: str | None = None


class RepresentativeFrame(BaseModel):
    """代表性帧（用于报告/绘图直接提取）。"""

    metric_key: str
    annotation_frame: int | None = None
    source_video_frame: int | None = None
    time_sec: float | None = None
    value: float | None = None
    extractable: bool = False
    mapping_status: Literal["verified", "unverified", "unknown"] = "unknown"
    reason: str | None = None


class ReferenceBodyLength(BaseModel):
    """参考体长（像素），用于归一化类指标的质量与上限。"""

    value_px: float | None = None
    sample_count: int = 0
    availability: Literal["available", "low_confidence", "unavailable"] = "unavailable"
    confidence: float = 0.0
    source_frames: list[int] = Field(default_factory=list)


class MetricSourceInfo(BaseModel):
    """指标来源标注与修订状态（revision_status 在 API 响应中计算，不持久化）。"""

    normalized_annotation_id: int
    revision: int
    revision_status: Literal["current", "stale", "unknown"] = "unknown"
    frame_mapping_status: Literal["verified", "unverified", "unknown"] = "unknown"
    stroke_type: str | None = None


class Side2DKinematicsResult(BaseModel):
    """side_2d_kinematics 计算器顶层输出，schema_version = swim-side-kinematics.v1。"""

    model_config = ConfigDict(extra="allow")

    schema_version: str = SCHEMA_SIDE_2D_KINEMATICS
    calculator: str = CALCULATOR_SIDE_2D_KINEMATICS
    calculator_version: str = CALCULATOR_VERSION_SIDE_2D
    camera_view: str = "side"

    source: MetricSourceInfo
    reference_body_length: ReferenceBodyLength | None = None
    summary: dict[str, MetricEnvelope] = Field(default_factory=dict)
    time_series: dict[str, list[KinematicSeriesPoint]] = Field(default_factory=dict)
    ranges: dict[str, MetricRange] = Field(default_factory=dict)
    representative_frames: dict[str, RepresentativeFrame] = Field(default_factory=dict)
    quality: dict = Field(default_factory=dict)


# ── 持久化读取结构 ──


class AnnotationMetricRead(BaseModel):
    """持久化后的 annotation_metrics 记录读取结构。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    normalized_annotation_id: int
    session_video_id: int | None = None
    schema_version: str
    camera_view: str
    metrics: dict
    quality: dict
    calculator: str
    calculator_version: str
    source_revision: int | None = None
    revision_status: Literal["current", "stale", "unknown"] | None = None
    created_by: int | None = None


class CalculateMetricsResponse(BaseModel):
    """calculate-metrics 端点响应。persist=false 时 annotation_metric_id 为 None。"""

    annotation_metric_id: int | None = None
    normalized_annotation_id: int
    schema_version: str
    camera_view: str
    calculator: str = CALCULATOR_SIDE_VIEW_METRICS
    calculator_version: str = CALCULATOR_VERSION_SIDE_VIEW
    source_revision: int | None = None
    revision_status: Literal["current", "stale", "unknown"] | None = None
    metrics: dict
    quality: dict


class MetricError(BaseModel):
    """非 side 视角或缺少核心前置条件时的错误响应。"""

    detail: str
    code: str
    quality: dict = Field(default_factory=dict)
