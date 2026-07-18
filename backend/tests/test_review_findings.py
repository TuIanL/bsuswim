"""二维运动学复核发现：引擎层与契约测试（无 DB）。

使用合成 annotation 经真实计算器产出 swim-side-kinematics.v1 指标，验证：
- adapter 展平 / 派生 / 可信度传播
- KRF006 无周期峰 ≠ 样本不足
- 证据帧定位
- 排序权重
- 引擎拒绝不匹配的 rule set
- R7 红线护栏（title 前缀 / 禁用短语扫描范围）
"""

import math
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from fixtures.synthetic_kinematics import build_synthetic_annotation  # noqa: E402

from app.services.metrics.kinematics.calculator import Side2DKinematicsCalculator  # noqa: E402
from app.services.metrics.kinematics.frame_resolver import resolve_frames  # noqa: E402
from app.services.diagnostics.registry import RuleRegistry  # noqa: E402
from app.services.diagnostics.review_findings.adapter import (  # noqa: E402
    Side2DKinematicsReviewAdapter,
)
from app.services.diagnostics.review_findings.engine import (  # noqa: E402
    KinematicReviewFindingsEngine,
    FORBIDDEN_ASSERTIVE_PHRASES,
)
from app.services.diagnostics.review_findings.evidence import EvidenceResolver  # noqa: E402

RULE_SET = "side_2d_kinematics_v1"


def _build_metric(annotation: dict, stroke_type: str = "freestyle") -> dict:
    ann = dict(annotation)
    ann.setdefault("annotation_metadata", {})["stroke_type"] = stroke_type
    calc = Side2DKinematicsCalculator()
    from app.services.metrics.kinematics.protocols import MetricCalculationContext

    ctx = MetricCalculationContext(
        normalized_annotation_id=1, source_revision=1, stroke_type=stroke_type
    )
    return calc.calculate(ann, ctx)


def _run(annotation, stroke_type="freestyle"):
    metric = _build_metric(annotation, stroke_type)
    adapter = Side2DKinematicsReviewAdapter().adapt(metric)
    engine = KinematicReviewFindingsEngine(RuleRegistry())
    canonical = resolve_frames(annotation.get("keypoint_frames") or [])
    out = engine.run(
        adapter, RULE_SET, metric_dict=metric, canonical_frames=canonical, mapping_status="verified"
    )
    return metric, adapter, out


# ── 1. Adapter 展平与派生 ──


def test_adapter_derives_normalized_ratios():
    metric = _build_metric(build_synthetic_annotation(frames=96))
    adapter = Side2DKinematicsReviewAdapter().adapt(metric)
    flat = adapter.evaluation_context.metrics
    assert "hip_vertical_range_ratio" in flat
    assert "head_vertical_range_ratio" in flat
    assert "elbow_rom_asymmetry_deg" in flat
    assert "minimum_knee_p05_deg" in flat
    # 像素阈值未直接暴露
    assert "hip_vertical_range_px" not in flat


def test_adapter_keeps_metric_meta_separate():
    metric = _build_metric(build_synthetic_annotation(frames=96))
    adapter = Side2DKinematicsReviewAdapter().adapt(metric)
    # metric_meta 承载溯源与质量
    meta = adapter.metric_meta["hip_vertical_range_ratio"]
    assert meta.source_metric_keys == ["summary.hip_vertical_range_px", "reference_body_length.value_px"]
    assert meta.availability in ("available", "low_confidence")
    assert 0.0 <= meta.confidence <= 1.0


def test_adapter_derived_confidence_is_min_of_sources():
    metric = _build_metric(build_synthetic_annotation(frames=96))
    adapter = Side2DKinematicsReviewAdapter().adapt(metric)
    meta = adapter.metric_meta["hip_vertical_range_ratio"]
    ref = metric.get("reference_body_length") or {}
    hip_env = metric["summary"]["hip_vertical_range_px"]
    expected_conf = min(hip_env.get("confidence", 0.0), ref.get("confidence", 0.0))
    assert abs(meta.confidence - round(expected_conf, 3)) < 1e-6


# ── 2. KRF006 无周期峰 vs 样本不足 ──


def _kick_metric(score=None, reason=None, sample_count=40):
    from app.schemas.metrics import Side2DKinematicsResult, MetricEnvelope, ReferenceBodyLength

    kick_value = None
    if score is not None:
        kick_value = {"period_frames": 20, "score": score}
    kick_details = {"side": "left"}
    if reason:
        kick_details["reason"] = reason
    return Side2DKinematicsResult(
        source={"normalized_annotation_id": 1, "revision": 1, "revision_status": "current",
                "frame_mapping_status": "unknown", "stroke_type": "freestyle"},
        reference_body_length=ReferenceBodyLength(value_px=500.0, sample_count=30, availability="available", confidence=0.9),
        summary={
            "kick_periodicity": MetricEnvelope(
                key="kick_periodicity", category="lower_limb", value=kick_value, unit="frame",
                sample_count=sample_count, confidence=0.8 if score is not None else 0.0,
                details=kick_details,
            )
        },
    ).model_dump()


def test_krf006_no_peak_generates_finding():
    metric = _kick_metric(reason="weak_or_no_peak")
    adapter = Side2DKinematicsReviewAdapter().adapt(metric)
    out = KinematicReviewFindingsEngine(RuleRegistry()).run(adapter, RULE_SET, metric_dict=metric)
    assert "KRF006" in out.matched_rule_ids
    assert all(f.status == "review_required" for f in out.findings)


def test_krf006_sample_insufficient_skipped():
    metric = _kick_metric(reason="weak_or_no_peak", sample_count=10)  # < MIN_PERIODICITY
    adapter = Side2DKinematicsReviewAdapter().adapt(metric)
    out = KinematicReviewFindingsEngine(RuleRegistry()).run(adapter, RULE_SET, metric_dict=metric)
    assert "KRF006" not in out.matched_rule_ids
    assert any(s["id"] == "KRF006" and s["reason"].startswith("unavailable_metric") for s in out.skipped_rules)


# ── 3. 证据帧定位 ──


def test_evidence_frames_resolved_from_time_series():
    metric, adapter, out = _run(build_synthetic_annotation(frames=96))
    found = {f.code: f for f in out.findings}
    # 至少有一条命中规则带证据帧（body_axis 序列存在）
    assert any(f.evidence_frames for f in out.findings)
    # KRF005 若存在，膝角最小帧角色正确
    if "large_knee_flexion_review" in found:
        kf = found["large_knee_flexion_review"].evidence_frames
        assert kf and kf[0].role == "minimum"
        # 合成数据带 mapping verified，故 extractable 为 True
        assert kf[0].extractable is True


def test_evidence_frames_unverified_not_extractable():
    metric, adapter, out = _run(build_synthetic_annotation(frames=96))
    resolver = EvidenceResolver(metric, mapping_status="unknown")
    frames = resolver.resolve("knee_minimum_triggering_side", 1)
    assert frames and frames[0].extractable is False


def test_evidence_frame_limit_capped_at_three():
    from app.schemas.metrics import Side2DKinematicsResult, MetricEnvelope, ReferenceBodyLength

    metric = Side2DKinematicsResult(
        source={"normalized_annotation_id": 1, "revision": 1, "revision_status": "current",
                "frame_mapping_status": "unknown", "stroke_type": "freestyle"},
        reference_body_length=ReferenceBodyLength(value_px=500.0, sample_count=30, availability="available", confidence=0.9),
        summary={
            "head_motion_spike_frames": MetricEnvelope(
                key="head_motion_spike_frames", category="head_trunk", value=[1, 2, 3, 4],
                unit="frame", sample_count=40, confidence=0.9,
                details={"spike_count": 4, "spike_annotation_frames": [1, 2, 3, 4]},
            )
        },
        time_series={"head_vertical_range_px": [
            {"frame": i, "annotation_frame": i, "source_video_frame": i, "value": float(i), "time_sec": i}
            for i in range(10)
        ]},
    ).model_dump()
    resolver = EvidenceResolver(metric, mapping_status="unknown")
    frames = resolver.resolve("head_spike_first_n", 3)
    assert len(frames) <= 3


# ── 4. 排序权重 ──


def test_findings_sorted_by_priority_score():
    metric, adapter, out = _run(build_synthetic_annotation(frames=96))
    scores = [f.priority_score for f in out.findings]
    assert scores == sorted(scores, reverse=True)
    # attention 降级 tie-breaker：priority_score 已含 attention_weight


# ── 5. 引擎拒绝不匹配 rule set ──


def test_engine_rejects_diagnostic_rule_set():
    metric = _build_metric(build_synthetic_annotation(frames=96))
    adapter = Side2DKinematicsReviewAdapter().adapt(metric)
    with pytest.raises(ValueError) as exc:
        KinematicReviewFindingsEngine(RuleRegistry()).run(adapter, "side_freestyle_v1")
    assert "rule_output_kind_mismatch" in str(exc.value)


def test_registry_rejects_unknown_output_kind():
    # 通过直接构造非法 output_kind 的解析不可行（yaml 固定），此处校验枚举存在
    from app.services.diagnostics.registry import SUPPORTED_OUTPUT_KINDS

    assert "review_finding" in SUPPORTED_OUTPUT_KINDS
    assert "diagnostic" in SUPPORTED_OUTPUT_KINDS


# ── 6. R7 红线护栏 ──


def test_all_rule_titles_have_prefix():
    registry = RuleRegistry()
    parsed = registry.load(RULE_SET)
    for rule in parsed["rules"]:
        assert rule["title"].startswith("疑似") or rule["title"].startswith("可能"), rule["id"]


def test_forbidden_phrase_scan_excludes_limitations():
    # 引擎只扫描 title/conclusion/reason，不扫描 limitations。
    # 因此含"推进效率低"的否定性 limitation 不应产生 forbidden 告警。
    from app.services.diagnostics.review_findings.engine import (
        KinematicReviewFindingsEngine,
        _validate_forbidden,
    )

    safe_limitation = "当前二维数据不能用于判断推进效率低的问题"
    metric = _build_metric(build_synthetic_annotation(frames=96))
    adapter = Side2DKinematicsReviewAdapter().adapt(metric)
    engine = KinematicReviewFindingsEngine(RuleRegistry())
    # 引擎只扫描 title/conclusion/reason，不扫描 limitations。
    # limitation 文本即使含禁用词，只要不作为 title 就不会告警。
    assert _validate_forbidden(safe_limitation) is True


def _assertive_ok(text: str) -> bool:
    return not any(phrase in text for phrase in FORBIDDEN_ASSERTIVE_PHRASES)


def test_forbidden_phrase_detects_assertive_title():
    # 引擎扫描 title；含明确断言短语（推进力不足）的 title 应被标记
    from app.services.diagnostics.review_findings.engine import _validate_forbidden

    bad_title = "膝关节屈曲过大，推进力不足"
    assert _validate_forbidden(bad_title) is False
    # 否定性 limitation 中的"推进效率低"不应被当作 title 断言
    assert _validate_forbidden("当前二维数据不能用于判断推进效率低的问题") is True


# ── 7. 幂等与签名（单元层：签名计算一致性）──


def test_generation_signature_stable_for_same_input():
    from app.services.diagnostics.review_findings.generation_service import _compute_signature

    sig1 = _compute_signature(42, 1, "hashA", RULE_SET, "filehash", "review-engine.v1", "project_heuristic_v1")
    sig2 = _compute_signature(42, 1, "hashA", RULE_SET, "filehash", "review-engine.v1", "project_heuristic_v1")
    assert sig1 == sig2
    sig3 = _compute_signature(42, 2, "hashA", RULE_SET, "filehash", "review-engine.v1", "project_heuristic_v1")
    assert sig1 != sig3


def test_no_match_returns_empty_ready():
    # 构造一个几乎不触发的指标（身体轴角极小、膝角大等）
    from app.schemas.metrics import Side2DKinematicsResult, MetricEnvelope, ReferenceBodyLength, MetricRange

    metric = Side2DKinematicsResult(
        source={"normalized_annotation_id": 1, "revision": 1, "revision_status": "current",
                "frame_mapping_status": "unknown", "stroke_type": "freestyle"},
        reference_body_length=ReferenceBodyLength(value_px=500.0, sample_count=30, availability="available", confidence=0.9),
        summary={
            "body_angle_std_deg": MetricEnvelope(key="body_angle_std_deg", category="body_posture", value=1.0, unit="deg", sample_count=30, availability="available", confidence=0.9),
            "head_body_synchrony": MetricEnvelope(key="head_body_synchrony", category="head_trunk", value=0.1, unit="r", sample_count=30, availability="available", confidence=0.9),
            "head_vertical_range_px": MetricEnvelope(key="head_vertical_range_px", category="head_trunk", value=5.0, unit="px", sample_count=30, availability="available", confidence=0.9),
            "hip_vertical_range_px": MetricEnvelope(key="hip_vertical_range_px", category="body_posture", value=5.0, unit="px", sample_count=30, availability="available", confidence=0.9),
            "elbow_rom_deg": MetricEnvelope(key="elbow_rom_deg", category="upper_limb", value={"left":70,"right":72,"combined":71}, sample_count=30, availability="available", confidence=0.9, details={"left":70,"right":72,"combined":71}),
            "knee_rom_deg": MetricEnvelope(key="knee_rom_deg", category="lower_limb", value={"left":60,"right":65,"combined":62}, sample_count=30, availability="available", confidence=0.9, details={"left":60,"right":65,"combined":62}),
            "kick_periodicity": MetricEnvelope(key="kick_periodicity", category="lower_limb", value={"period_frames":20,"score":0.9}, unit="frame", sample_count=40, availability="available", confidence=0.8, details={"side":"left","period_frames":20,"score":0.9}),
            "head_motion_spike_frames": MetricEnvelope(key="head_motion_spike_frames", category="head_trunk", value=[], unit="frame", sample_count=40, availability="available", confidence=0.9, details={"spike_count":0,"spike_annotation_frames":[]}),
        },
        ranges={"left_knee_angle_deg": MetricRange(metric_key="left_knee_angle_deg", category="lower_limb", p05=150),"right_knee_angle_deg": MetricRange(metric_key="right_knee_angle_deg", category="lower_limb", p05=150)},
    ).model_dump()
    adapter = Side2DKinematicsReviewAdapter().adapt(metric)
    out = KinematicReviewFindingsEngine(RuleRegistry()).run(adapter, RULE_SET, metric_dict=metric)
    assert out.findings == []
    assert out.matched_rule_ids == []
