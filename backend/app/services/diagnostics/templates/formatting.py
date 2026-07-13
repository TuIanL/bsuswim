"""模板渲染辅助：把规则模板里的 ``{metric_key}`` 占位符替换为带单位的格式化值。

规则 YAML 的 ``evidence_template`` / ``reason_template`` / ``suggestion_template`` 使用
``{body_angle_deg}`` 这类稳定逻辑键占位符。本模块负责安全替换：

- 指标存在 → 按单位格式化（° / cm / m / spm / hz）
- 指标缺失（None）→ 用降级占位 ``—``，不抛异常（满足“可选指标缺失时提供降级文案”）
"""

import re

# 稳定逻辑键 → 单位
_UNIT_MAP: dict[str, str] = {
    "body_angle_deg": "°",
    "hip_depth_cm": " cm",
    "elbow_angle_deg": "°",
    "forearm_drop_angle_deg": "°",
    "knee_angle_deg": "°",
    "hip_angle_deg": "°",
    "entry_angle_deg": "°",
    "ankle_extension_angle_deg": "°",
    "front_reach_distance_cm": " cm",
    "stroke_length_m": " m",
    "stroke_rate_spm": " spm",
    "kick_frequency_hz": " hz",
    "average_speed_mps": " m/s",
    "swolf_value": "",
}

_TOKEN = re.compile(r"\{(\w+)\}")


def format_metric(key: str, value: object) -> str:
    """把单个指标键格式化为带单位的字符串；缺失返回降级占位。"""
    if value is None:
        return "—"
    unit = _UNIT_MAP.get(key, "")
    if isinstance(value, float):
        # 去掉无意义的小数尾巴
        if value == int(value):
            return f"{int(value)}{unit}"
        return f"{value:.2f}{unit}"
    return f"{value}{unit}"


def render_template(template: str, metrics: dict) -> str:
    """把模板中的 ``{key}`` 替换为格式化值；缺失键用降级占位。"""
    if not template:
        return ""

    def _repl(match: re.Match) -> str:
        key = match.group(1)
        return format_metric(key, metrics.get(key))

    return _TOKEN.sub(_repl, template)
