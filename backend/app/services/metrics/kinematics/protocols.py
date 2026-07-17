"""side_2d_kinematics calculator 协议与计算上下文。

与旧 ``calculate_side_view_metrics(annotation, view_type)`` 函数签名解耦：
所有计算器统一为 ``calculate(annotation, context) -> dict``，由 registry 路由。
"""

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class MetricCalculationContext:
    """一次指标计算所需的上下文（不进入指标 schema，仅用于计算与持久化）。"""

    normalized_annotation_id: int
    source_revision: int
    camera_view: str = "side"
    annotation_metadata: dict = field(default_factory=dict)
    frame_mapping: dict | None = None
    stroke_type: str | None = None


class MetricCalculator(Protocol):
    """计算器协议（结构化子类型，无需显式继承）。"""

    name: str
    version: str
    schema_version: str

    def calculate(self, annotation: dict, context: MetricCalculationContext) -> dict:
        """计算并返回指标 dict（顶层应含 calculator / calculator_version /
        schema_version 等字段，便于 service 持久化）。"""
        ...
