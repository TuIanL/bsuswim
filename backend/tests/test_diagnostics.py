"""规则诊断引擎测试。

- 单测（无 DB）：adapter 映射、severity 部分评估、active/dormant/缺指标跳过、
  R006+R008 合并、§9 验收样例、phase_context 细分跳过原因。
- 集成测试（标记 integration，需真实 Postgres）：bridge 解析 side AnnotationMetric 并写回。

引擎层不依赖数据库，直接用 ``DiagnosticMetricsContext`` 测试，便于本地验证。
"""

import os

import pytest

from app.services.diagnostics.adapter import DiagnosticsMetricsAdapter
from app.services.diagnostics.engine import RuleBasedDiagnosticsEngine
from app.services.diagnostics.models import DiagnosticMetricsContext
from app.services.diagnostics.registry import RuleRegistry

RULE_SET = "side_freestyle_v1"


def _adapter() -> DiagnosticsMetricsAdapter:
    return DiagnosticsMetricsAdapter()


def _engine() -> RuleBasedDiagnosticsEngine:
    return RuleBasedDiagnosticsEngine(RuleRegistry())


def _ctx(metrics: dict, manual_tags=None, quality=None, phase_context=None) -> DiagnosticMetricsContext:
    return DiagnosticMetricsContext(
        metrics=metrics,
        manual_tags=manual_tags or [],
        quality_summary=quality or {},
        phase_context=phase_context,
    )


# ──────────────────────────────────────────────────────────────────────────
# 10.2 adapter 映射
# ──────────────────────────────────────────────────────────────────────────


def test_adapter_maps_summary_avg_keys_to_stable_logical_keys():
    metrics = {
        "summary": {
            "body_angle_deg_avg": 14.0,
            "hip_depth_cm_avg": 9.0,
            "elbow_angle_deg_avg": 154.0,
            "forearm_drop_angle_deg_avg": 24.0,
            "knee_angle_deg_avg": 114.0,
            "stroke_rate_spm_avg": 82.5,
            "stroke_length_m_avg": 1.06,
            "front_reach_distance_cm_avg": 70.0,
            "kick_frequency_hz": 1.2,
        }
    }
    ctx = _adapter().adapt(metrics)
    assert ctx.metrics["body_angle_deg"] == 14.0
    assert ctx.metrics["hip_depth_cm"] == 9.0
    assert ctx.metrics["elbow_angle_deg"] == 154.0
    assert ctx.metrics["forearm_drop_angle_deg"] == 24.0
    assert ctx.metrics["knee_angle_deg"] == 114.0
    assert ctx.metrics["stroke_rate_spm"] == 82.5
    assert ctx.metrics["stroke_length_m"] == 1.06
    assert ctx.metrics["front_reach_distance_cm"] == 70.0
    assert ctx.metrics["kick_frequency_hz"] == 1.2


def test_adapter_flattens_swolf_value():
    metrics = {"summary": {"swolf": {"value": 88.0, "time_sec": 12.0, "stroke_count": 30}}}
    ctx = _adapter().adapt(metrics)
    assert ctx.metrics["swolf_value"] == 88.0
    assert ctx.missing_or_unsupported_metrics == []


def test_adapter_records_missing_swolf_value():
    metrics = {"summary": {"swolf": {"time_sec": 12.0}}}  # 无 value
    ctx = _adapter().adapt(metrics)
    assert "swolf_value" not in ctx.metrics
    assert ctx.missing_or_unsupported_metrics == ["swolf_value"]


def test_adapter_manual_tags_authoritative_from_normalized_annotation():
    # NormalizedAnnotation.manual_tags 优先；metrics 内残留仅在空时回退
    metrics = {"summary": {}, "manual_tags": ["stale_tag"]}
    ctx = _adapter().adapt(metrics, manual_tags=["front_arm_drop", "low_elbow_catch"])
    assert ctx.manual_tags == ["front_arm_drop", "low_elbow_catch"]

    # 权威来源为空 → 回退 metrics 残留
    ctx2 = _adapter().adapt(metrics, manual_tags=[])
    assert ctx2.manual_tags == ["stale_tag"]


def test_adapter_preserves_phase_context():
    metrics = {"summary": {}, "phase_metrics": [{"phase_key": "low_speed", "speed_mps": 1.0}]}
    ctx = _adapter().adapt(metrics)
    assert ctx.phase_context == metrics["phase_metrics"]


# ──────────────────────────────────────────────────────────────────────────
# 10.3 active 命中 / dormant / 缺指标 跳过
# ──────────────────────────────────────────────────────────────────────────


def test_manual_tag_trigger_fires_rule():
    # R004 的 manual_tag 分支（前臂下压）独立触发，即便 metric 不满足阈值
    metrics = {"forearm_drop_angle_deg": 5.0}  # 远低于 20 阈值
    ctx = _ctx(metrics, manual_tags=["前臂下压"])
    out = _engine().run(ctx)
    codes = [d.code for d in out.diagnostics]
    assert "forearm_press_down" in codes


def test_dormant_rule_skipped_with_reason():
    out = _engine().run(_ctx({}))
    reasons = {s.id: s.reason for s in out.skipped_rules}
    assert reasons.get("R005") == "dormant"


def test_missing_required_metric_skipped_with_reason():
    out = _engine().run(_ctx({}))  # 无任何指标
    reasons = {s.id: s.reason for s in out.skipped_rules}
    assert reasons.get("R007") == "missing_metric:catch_area_score"
    assert reasons.get("R010") == "missing_metric:kick_interval_cv"
    assert reasons.get("R011") == "missing_metric:stroke_rate_by_phase,stroke_length_by_phase"


def test_phase_context_skip_reason_taxonomy():
    # None → missing
    out = _engine().run(_ctx({}))
    reasons = {s.id: s.reason for s in out.skipped_rules}
    assert reasons.get("R003") == "missing_metric:phase_context"

    # 仅 1 桶 → insufficient speed_buckets
    out2 = _engine().run(_ctx({}, phase_context=[{"phase_key": "low_speed", "speed_mps": 1.0}]))
    reasons2 = {s.id: s.reason for s in out2.skipped_rules}
    assert reasons2.get("R003") == "insufficient_metric:phase_context.speed_buckets"

    # 2 桶但无 speed_mps → insufficient distance_markers
    out3 = _engine().run(_ctx({}, phase_context=[{"phase_key": "low_speed"}, {"phase_key": "high_speed"}]))
    reasons3 = {s.id: s.reason for s in out3.skipped_rules}
    assert reasons3.get("R003") == "insufficient_metric:phase_context.distance_markers"


def test_severity_partial_eval_when_branch_metric_missing():
    # R012 的 high 分支含 efficiency_score（缺失），应忽略该分支，仅用 swolf_value 判 medium
    metrics = {"swolf_value": 88.0}  # >85 medium, >90 high；无 efficiency_score
    out = _engine().run(_ctx(metrics))
    r012 = next(d for d in out.diagnostics if d.code == "low_swim_efficiency")
    assert r012.severity == "medium"
    assert any("efficiency_score" in w for w in out.partial_evaluation_warnings)


# ──────────────────────────────────────────────────────────────────────────
# 7.4 / §5.1 R006 + R008 合并
# ──────────────────────────────────────────────────────────────────────────


def test_r006_r008_merged_into_single_upper_limb_diagnostic():
    metrics = {"elbow_angle_deg": 154.0, "stroke_length_m": 1.06}
    out = _engine().run(_ctx(metrics))
    codes = [d.code for d in out.diagnostics]
    assert "insufficient_high_elbow_catch" in codes
    # 不应出现两条并列的上肢推进问题
    assert "low_propulsive_efficiency" not in codes
    primary = next(d for d in out.diagnostics if d.code == "insufficient_high_elbow_catch")
    assert primary.title == "高肘抱水不足，影响上肢推进效率"
    assert primary.related_diagnostics and primary.related_diagnostics[0]["code"] == "low_propulsive_efficiency"


# ──────────────────────────────────────────────────────────────────────────
# 10.5 §9 验收样例（真实 Task #4 键形态）
# ──────────────────────────────────────────────────────────────────────────


def _section9_context() -> DiagnosticMetricsContext:
    metrics = {
        "schema_version": "swim-side-metrics.v1",
        "summary": {
            "body_angle_deg_avg": 14.0,
            "hip_depth_cm_avg": 9.0,
            "elbow_angle_deg_avg": 154.0,
            "forearm_drop_angle_deg_avg": 24.0,
            "knee_angle_deg_avg": 114.0,
            "stroke_rate_spm_avg": 82.5,
            "stroke_length_m_avg": 1.06,
            "swolf": {"value": 88.0},
        },
    }
    return _adapter().adapt(metrics, manual_tags=["front_arm_drop", "low_elbow_catch"])


def test_section9_expected_hits_and_skips():
    out = _engine().run(_section9_context())

    # 命中的 7 条规则
    assert set(out.matched_rule_ids) == {
        "R001", "R002", "R004", "R006", "R008", "R009", "R012"
    }

    # 跳过原因与 §9 一致
    reasons = {s.id: s.reason for s in out.skipped_rules}
    assert reasons == {
        "R003": "missing_metric:phase_context",
        "R005": "dormant",
        "R007": "missing_metric:catch_area_score",
        "R010": "missing_metric:kick_interval_cv",
        "R011": "missing_metric:stroke_rate_by_phase,stroke_length_by_phase",
    }

    # 最终 diagnostics 不含并列的上肢推进问题（R006+R008 已合并）
    codes = [d.code for d in out.diagnostics]
    assert "low_propulsive_efficiency" not in codes
    assert "insufficient_high_elbow_catch" in codes

    # 身体位置偏低（high）排在最前
    assert out.diagnostics[0].code == "low_body_position"
    assert out.summary.overall_risk_level == "high"


# ──────────────────────────────────────────────────────────────────────────
# 10.4 bridge 集成（需真实 Postgres；无 DATABASE_URL 时跳过）
# ──────────────────────────────────────────────────────────────────────────


@pytest.mark.integration
@pytest.mark.skipif(not os.environ.get("DATABASE_URL"), reason="需要 DATABASE_URL 指向真实 Postgres")
def test_bridge_resolves_side_metrics_and_writes_back(db_session):
    """端到端：bridge 从 AnalysisResult 解析 side AnnotationMetric 并写回诊断。"""
    from datetime import timezone

    from app.models import (
        AnalysisResult,
        AnalysisTask,
        AnnotationMetric,
        Athlete,
        NormalizedAnnotation,
        TrainingSession,
        User,
        VideoFile,
    )
    from app.models.video import SessionVideo, ViewType
    from app.services.diagnostics.bridge import run_diagnostics_for_analysis_result

    # 最小化种子数据
    coach = User(username="diag_coach", email="diag@example.com", password_hash="x",
                 full_name="c", role="COACH", is_active=True)
    db_session.add(coach)
    db_session.flush()
    athlete = Athlete(name="diag_athlete", coach_id=coach.id)
    db_session.add(athlete)
    db_session.flush()
    session = TrainingSession(athlete_id=athlete.id, coach_id=coach.id, title="t", stroke_type="freestyle")
    db_session.add(session)
    db_session.flush()
    task = AnalysisTask(session_id=session.id, status="completed")
    db_session.add(task)
    db_session.flush()
    result = AnalysisResult(task_id=task.id, schema_version="x", detections=[], keypoint_frames=[],
                            phases=[], metrics={}, diagnostics=[], raw_result={})
    db_session.add(result)
    db_session.flush()
    video_file = VideoFile(
        original_filename="diag_test.mp4",
        stored_filename="diag_test.mp4",
        storage_path="/tmp/diag_test.mp4",
        mime_type="video/mp4",
        size_bytes=1024,
        checksum_sha256="x" * 64,
    )
    db_session.add(video_file)
    db_session.flush()
    video = SessionVideo(session_id=session.id, video_file_id=video_file.id, view_type=ViewType.SIDE)
    db_session.add(video)
    db_session.flush()
    norm = NormalizedAnnotation(session_video_id=video.id, revision=1,
                                schema_version="swim-annotation.v1", source="kinovea", fps=30)
    db_session.add(norm)
    db_session.flush()
    ann_metric = AnnotationMetric(
        normalized_annotation_id=norm.id,
        session_video_id=video.id,
        schema_version="swim-side-metrics.v1",
        metrics={
            "summary": {
                "body_angle_deg_avg": 14.0,
                "elbow_angle_deg_avg": 154.0,
                "stroke_length_m_avg": 1.06,
                "swolf": {"value": 88.0},
            }
        },
        quality={},
    )
    db_session.add(ann_metric)
    db_session.commit()

    out = run_diagnostics_for_analysis_result(db_session, result.id, overwrite=True)
    assert "R001" in out.matched_rule_ids

    db_session.refresh(result)
    assert len(result.diagnostics) >= 1
    meta = (result.raw_result or {}).get("diagnostics_meta")
    assert meta and meta["matched_rule_ids"]
    assert "quality_summary" in result.__dict__
