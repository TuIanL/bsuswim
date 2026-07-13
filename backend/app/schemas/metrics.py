"""Side-view metrics output schemas.

这些 schema 仅描述**事实测量值**，不含任何诊断结论。Change #5（规则诊断）
与 Change #6（报告装配）读取本层产出的 metrics 后再各自生成结论。
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


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


class SideViewMetrics(BaseModel):
    """side-view metrics 的固定输出结构，schema_version = swim-side-metrics.v1。"""

    model_config = ConfigDict(extra="allow")

    schema_version: str = "swim-side-metrics.v1"
    camera_view: str = "side"
    summary: dict = Field(default_factory=dict)
    time_series: dict = Field(default_factory=dict)
    cycles: list[dict] = Field(default_factory=list)
    phase_metrics: list[dict] = Field(default_factory=list)
    quality: dict = Field(default_factory=dict)


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
    created_by: int | None = None


class CalculateMetricsResponse(BaseModel):
    """calculate-metrics 端点响应。persist=false 时 annotation_metric_id 为 None。"""

    annotation_metric_id: int | None = None
    normalized_annotation_id: int
    schema_version: str
    camera_view: str
    metrics: dict
    quality: dict


class MetricError(BaseModel):
    """非 side 视角或缺少核心前置条件时的错误响应。"""

    detail: str
    code: str
    quality: dict = Field(default_factory=dict)
