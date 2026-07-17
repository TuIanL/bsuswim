"""计算器注册表。

替代旧的硬编码路由：``calculate_and_persist`` 通过名字从注册表取得计算器，
``?calculator=`` 参数可切换。旧 ``side_view_metrics`` 与新 ``side_2d_kinematics``
并存，互不干扰。

为避免循环导入，内置计算器在 ``register_builtin_calculators()`` 中惰性注册，
该函数应在应用启动或首次计算前被调用（service 层会确保调用）。
"""

from typing import Any

from app.schemas.metrics import (
    CALCULATOR_SIDE_2D_KINEMATICS,
    CALCULATOR_SIDE_VIEW_METRICS,
    SCHEMA_SIDE_2D_KINEMATICS,
    SCHEMA_SIDE_METRICS,
)
from app.services.metrics.kinematics.protocols import (
    MetricCalculationContext,
    MetricCalculator,
)


_REGISTRY: dict[str, MetricCalculator] = {}
_REGISTERED = False


class _LegacySideViewMetricsCalculator:
    """适配器：把旧 ``calculate_side_view_metrics(annotation, view_type)`` 包成协议。"""

    name = CALCULATOR_SIDE_VIEW_METRICS
    version = "0.1.0"
    schema_version = SCHEMA_SIDE_METRICS

    def calculate(self, annotation: dict, context: MetricCalculationContext) -> dict:
        from app.services.metrics.engine import calculate_side_view_metrics

        view_type = context.camera_view if context else "side"
        result = calculate_side_view_metrics(annotation, view_type)
        result.setdefault("calculator", self.name)
        result.setdefault("calculator_version", self.version)
        result.setdefault("schema_version", self.schema_version)
        return result


class _Side2DKinematicsCalculatorAdapter:
    """适配器：包装真正的 Side2DKinematicsCalculator，统一注册入口。"""

    name = CALCULATOR_SIDE_2D_KINEMATICS
    version = "1.0.0"
    schema_version = SCHEMA_SIDE_2D_KINEMATICS

    def calculate(self, annotation: dict, context: MetricCalculationContext) -> dict:
        from app.services.metrics.kinematics.calculator import Side2DKinematicsCalculator

        return Side2DKinematicsCalculator().calculate(annotation, context)


def register(calculator: MetricCalculator) -> MetricCalculator:
    _REGISTRY[calculator.name] = calculator
    return calculator


def get_calculator(name: str) -> MetricCalculator:
    if name not in _REGISTRY:
        raise KeyError(name)
    return _REGISTRY[name]


def has_calculator(name: str) -> bool:
    return name in _REGISTRY


def list_calculators() -> list[str]:
    return list(_REGISTRY.keys())


def register_builtin_calculators() -> None:
    """注册内置计算器（幂等）。应在应用启动 / 首次计算前调用。"""
    global _REGISTERED
    if _REGISTERED:
        return
    register(_LegacySideViewMetricsCalculator())
    register(_Side2DKinematicsCalculatorAdapter())
    _REGISTERED = True
