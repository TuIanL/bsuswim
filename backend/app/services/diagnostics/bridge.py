"""analysis_result 接线桥（质量聚合 + 规则诊断）。

数据路径：
    task.request_payload.analysis_input (含 annotation quality snapshot)
    + AnnotationMetric.quality (metric quality)
    → AnalysisQualityAggregator
    → AnalysisResult.quality_summary
    → RuleBasedDiagnosticsEngine
"""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    AnalysisResult,
    AnalysisTask,
    AnnotationMetric,
    NormalizedAnnotation,
    TrainingSession,
)
from app.models.video import ViewType
from app.services.annotation_quality.aggregator import AnalysisQualityAggregator
from app.services.annotation_quality.legacy import normalize_quality_payload
from app.services.annotation_quality.models import AnalysisQualitySummary, MetricQualityReport
from app.services.diagnostics.adapter import DiagnosticsMetricsAdapter
from app.services.diagnostics.engine import RuleBasedDiagnosticsEngine
from app.services.diagnostics.models import DiagnosticsOutput
from app.services.diagnostics.registry import RuleRegistry

DEFAULT_RULE_SET = "side_freestyle_v1"
_DIAGNOSTICS_VERSION = "swim-side-metrics.v1"


class DiagnosticsBridgeError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class AnnotationQualityBlockedError(Exception):
    def __init__(self, quality: dict):
        self.quality = quality
        super().__init__("标注质量不足，无法运行诊断")


def run_diagnostics_for_analysis_result(
    db: Session,
    analysis_result_id: int,
    rule_set: str = DEFAULT_RULE_SET,
    overwrite: bool = True,
    force: bool = False,
) -> DiagnosticsOutput:
    result = db.get(AnalysisResult, analysis_result_id)
    if result is None:
        raise DiagnosticsBridgeError(404, "分析结果不存在")

    existing = result.diagnostics
    if existing and len(existing) > 0 and not overwrite:
        raise DiagnosticsBridgeError(409, "已有诊断结果，需显式 overwrite=true 覆盖")

    task: AnalysisTask | None = result.task
    if task is None:
        raise DiagnosticsBridgeError(422, "分析结果未关联分析任务")

    session: TrainingSession | None = task.session
    if session is None:
        raise DiagnosticsBridgeError(422, "分析任务未关联训练记录")

    # ── T2 snapshot: annotation quality from task ──
    analysis_input = (task.request_payload or {}).get("analysis_input", {})
    annotation_id = analysis_input.get("annotation_id")
    quality_snapshot = analysis_input.get("annotation_quality_snapshot")

    if not quality_snapshot and annotation_id:
        norm = db.get(NormalizedAnnotation, annotation_id)
        if norm:
            quality_snapshot = norm.quality

    annotation_quality = normalize_quality_payload(quality_snapshot)

    # ── quality gate ──
    if annotation_quality.status == "invalid" and not force:
        raise AnnotationQualityBlockedError(annotation_quality.model_dump(mode="json"))

    # ── T3: metric quality ──
    side_video = next((v for v in session.videos if v.view_type == ViewType.SIDE), None)
    if side_video is None:
        raise DiagnosticsBridgeError(422, "训练记录无 side 机位视频")

    norm = db.scalars(
        select(NormalizedAnnotation)
        .where(NormalizedAnnotation.session_video_id == side_video.id)
        .order_by(NormalizedAnnotation.id.desc())
    ).first()
    if norm is None:
        raise DiagnosticsBridgeError(422, "side 机位无标准化标注")

    ann_metric = db.scalars(
        select(AnnotationMetric)
        .where(
            AnnotationMetric.normalized_annotation_id == norm.id,
            AnnotationMetric.schema_version == _DIAGNOSTICS_VERSION,
        )
        .order_by(AnnotationMetric.id.desc())
    ).first()
    if ann_metric is None:
        raise DiagnosticsBridgeError(422, "side 标注无可用 side-view metrics")

    metric_quality_dict = ann_metric.quality if isinstance(ann_metric.quality, dict) else {}
    metric_quality = MetricQualityReport.model_validate(metric_quality_dict) if metric_quality_dict.get("schema_version") else None

    # ── T4: aggregate ──
    aggregator = AnalysisQualityAggregator()
    quality_summary: AnalysisQualitySummary = aggregator.aggregate(
        annotation_quality, metric_quality
    )

    result.quality_summary = quality_summary.model_dump(mode="json")

    # ── skip blocked modules ──
    module_avail = quality_summary.decision.module_availability
    blocked_modules = {
        mk for mk in ("body_position", "arm_entry", "catch_pull", "leg_kick", "efficiency")
        if getattr(module_avail, mk, None) == "blocked"
    }

    # ── run diagnostics ──
    adapter = DiagnosticsMetricsAdapter()
    context = adapter.adapt(
        ann_metric.metrics,
        manual_tags=norm.manual_tags,
        quality=norm.quality,
    )

    # inject quality context for rule engine
    qs_dict = quality_summary.model_dump(mode="json")
    context.quality_summary = qs_dict
    context.metric_quality = metric_quality.model_dump(mode="json") if metric_quality else {}
    context.quality_decision = qs_dict.get("decision", {})

    engine = RuleBasedDiagnosticsEngine(RuleRegistry())
    output = engine.run(context, rule_set=rule_set)

    # filter out diagnostics for blocked modules
    if blocked_modules:
        output.diagnostics = [
            d for d in output.diagnostics
            if d.section_key not in blocked_modules
        ]

    # ── write back ──
    result.diagnostics = [_dump(d) for d in output.diagnostics]

    if result.raw_result is None:
        result.raw_result = {}
    result.raw_result["diagnostics_meta"] = {
        "rule_set": rule_set,
        "rule_version": engine.registry.rule_version(rule_set),
        "engine_version": engine.engine_version,
        "matched_rule_ids": output.matched_rule_ids,
        "skipped_rule_ids": [_dump(s) for s in output.skipped_rules],
        "partial_evaluation_warnings": output.partial_evaluation_warnings,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "blocked_modules": list(blocked_modules),
    }

    db.add(result)
    db.commit()
    db.refresh(result)
    return output


def _dump(obj: Any) -> dict:
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    return dict(obj)
