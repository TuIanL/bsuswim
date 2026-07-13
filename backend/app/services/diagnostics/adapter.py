"""DiagnosticsMetricsAdapter：把 ``annotation_metrics`` 适配为 ``DiagnosticMetricsContext``。

契约层职责（Change #5 核心修正之一）：规则 YAML 永不直接绑定
``annotation_metrics.summary`` 的内部键（``body_angle_deg_avg`` / ``swolf.value`` /
``phase_metrics[]`` / ``front_reach_distance_cm_avg`` 等），只认 adapter 产出的稳定逻辑键
（``body_angle_deg`` / ``swolf_value`` 等）。未来 Task #4 内部键改名，或 AI 姿态识别直接产出
另一套 metrics，只需改本 adapter，规则库不动。

映射表（v1）：

    Task #4 实际键                      诊断逻辑键
    ─────────────────────────────      ─────────────────────────
    body_angle_deg_avg                  body_angle_deg
    hip_depth_cm_avg                    hip_depth_cm
    elbow_angle_deg_avg                 elbow_angle_deg
    forearm_drop_angle_deg_avg          forearm_drop_angle_deg
    knee_angle_deg_avg                  knee_angle_deg
    stroke_rate_spm_avg                 stroke_rate_spm
    stroke_length_m_avg                 stroke_length_m
    swolf.value                         swolf_value
    front_reach_distance_cm_avg         front_reach_distance_cm
    kick_frequency_hz                   kick_frequency_hz（直通）
    phase_metrics[]                     phase_context（保留嵌套，不解析）
    manual_tags (NormalizedAnnotation)  manual_tags（权威来源）
    quality                             quality_summary

``manual_tags`` 权威来源是 ``NormalizedAnnotation.manual_tags``；仅当其缺失/为空时，
才回退 ``annotation_metrics.metrics.manual_tags``（可能为旧标注残留）。
"""

from typing import Any, Optional

from app.services.diagnostics.models import DiagnosticMetricsContext

# summary 内部键 → 稳定逻辑键（重命名 / 展平）
_SUMMARY_RENAME: dict[str, str] = {
    "body_angle_deg_avg": "body_angle_deg",
    "hip_depth_cm_avg": "hip_depth_cm",
    "elbow_angle_deg_avg": "elbow_angle_deg",
    "forearm_drop_angle_deg_avg": "forearm_drop_angle_deg",
    "knee_angle_deg_avg": "knee_angle_deg",
    "stroke_rate_spm_avg": "stroke_rate_spm",
    "stroke_length_m_avg": "stroke_length_m",
    "front_reach_distance_cm_avg": "front_reach_distance_cm",
}

# 宽松透传（保持原键名，未来规则可能直接用）
_PASS_THROUGH_KEYS: tuple[str, ...] = (
    "entry_angle_deg_avg",
    "hip_angle_deg_avg",
    "ankle_extension_angle_deg_avg",
    "average_speed_mps",
    "streamline_index",
    "technical_stability_score",
    "stroke_cycle_duration_sec_avg",
    "stroke_count",
    "kick_frequency_hz",
)


class DiagnosticsMetricsAdapter:
    """将 side-view metrics 产物适配为诊断引擎稳定输入。"""

    def adapt(
        self,
        metrics_dict: dict[str, Any],
        manual_tags: Optional[list[str]] = None,
        quality: Optional[dict] = None,
    ) -> DiagnosticMetricsContext:
        """适配单条 ``annotation_metrics.metrics``。

        :param metrics_dict: AnnotationMetric.metrics（含 summary/phase_metrics/quality 等）
        :param manual_tags: 权威来源 ``NormalizedAnnotation.manual_tags``；为空时回退 metrics 内残留
        :param quality: 优先用传入的 NormalizedAnnotation.quality；否则用 metrics.quality
        """
        metrics_dict = metrics_dict or {}
        summary = metrics_dict.get("summary") or {}

        ctx_metrics: dict[str, Any] = {}
        missing_or_unsupported: list[str] = []

        # 1) 重命名映射的 summary 键
        for src, dst in _SUMMARY_RENAME.items():
            if src in summary and summary[src] is not None:
                ctx_metrics[dst] = summary[src]

        # 2) swolf 对象展平为 swolf_value
        swolf = summary.get("swolf")
        if isinstance(swolf, dict) and "value" in swolf and swolf["value"] is not None:
            ctx_metrics["swolf_value"] = swolf["value"]
        else:
            missing_or_unsupported.append("swolf_value")

        # 3) 宽松透传（未来规则可用）
        for key in _PASS_THROUGH_KEYS:
            if key in summary and summary[key] is not None:
                ctx_metrics[key] = summary[key]

        # 4) phase_context：保留嵌套 phase_metrics，不解析（供未来分速度段规则）
        phase_context = metrics_dict.get("phase_metrics")

        # 5) manual_tags：权威来源优先，回退 metrics 内残留
        final_tags: list[str] = []
        if manual_tags:
            final_tags = list(manual_tags)
        else:
            residual = metrics_dict.get("manual_tags")
            if isinstance(residual, list):
                final_tags = residual

        # 6) quality_summary：传入优先，回退 metrics.quality
        quality_summary = quality if quality is not None else (metrics_dict.get("quality") or {})

        return DiagnosticMetricsContext(
            metrics=ctx_metrics,
            manual_tags=final_tags,
            quality_summary=quality_summary if isinstance(quality_summary, dict) else {},
            phase_context=phase_context,
            missing_or_unsupported_metrics=missing_or_unsupported,
        )
