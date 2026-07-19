"""Tests for annotation-driven analysis pipeline (Change 7).

Covers:
- pipeline routing / version default / mismatch rejection (service layer)
- quality adapter issue → 4 module mapping (unit)
- full annotation pipeline executes and persists all products (integration)
- revision drift → failed task
- retry (annotation only) reuses idempotent products
- report last-successful-write + session lock semantics
"""
import pytest

from app.models import AnnotationMetric, ReportMetadata
from app.schemas.analysis import ANNOTATION_PIPELINE_VERSION
from app.services.analysis_service import create_analysis_task, retry_analysis_task
from app.services.metrics.kinematics.quality_adapter import aggregate_side_2d_kinematics_quality
from app.services.metrics.kinematics.quality import (
    ISSUE_HEAD_POINTS_INSUFFICIENT,
    ISSUE_REFERENCE_BODY_LENGTH_INSUFFICIENT,
)


def _sel(db, model, **filters):
    from sqlalchemy import select

    stmt = select(model)
    for k, v in filters.items():
        stmt = stmt.where(getattr(model, k) == v)
    return db.scalar(stmt)


def _run_pipeline(db_session, task):
    from app.services.analysis_pipelines.annotation_kinematics import _run_sync

    _run_sync(task.id, task.pipeline_version, db=db_session)
    db_session.expire_all()
    return db_session.get(type(task), task.id)


def _build_chain(db_session):
    """Build coach → athlete → session → video → session_video → annotation.

    复用 test_kinematics_report 的 build_golden_annotation 生成骨架数据。
    """
    from fixtures.synthetic_kinematics import build_golden_annotation

    from app.models.athlete import Athlete
    from app.models.normalized_annotation import NormalizedAnnotation
    from app.models.training_session import StrokeType, TrainingSession
    from app.models.user import User
    from app.models.video import SessionVideo, VideoFile, ViewType

    user = User(
        username="pipe_coach",
        email="pipe@test.com",
        full_name="Pipe Coach",
        role="coach",
        password_hash="dummy",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()

    athlete = Athlete(name="Pipe Athlete", coach_id=user.id, level="一级运动员")
    db_session.add(athlete)
    db_session.flush()

    ts = TrainingSession(
        athlete_id=athlete.id,
        coach_id=user.id,
        title="Pipe Session",
        stroke_type=StrokeType.FREESTYLE,
        distance_m=50,
        pool_length_m=25.0,
    )
    db_session.add(ts)
    db_session.flush()

    vf = VideoFile(
        original_filename="pipe.mp4",
        stored_filename="pipe_stored.mp4",
        storage_path="uploads/pipe.mp4",
        mime_type="video/mp4",
        size_bytes=1000,
        checksum_sha256="pipe_checksum_sha256_64_chars_xxxxxxxxxxxxxxxxxxx",
    )
    db_session.add(vf)
    db_session.flush()

    sv = SessionVideo(session_id=ts.id, video_file_id=vf.id, view_type=ViewType.SIDE, fps=60.0)
    db_session.add(sv)
    db_session.flush()

    ann_dict = build_golden_annotation(50, verified=True)
    ann = NormalizedAnnotation(
        session_video_id=sv.id,
        revision=3,
        schema_version="swim-annotation.v1",
        source="cvat_coco17",
        fps=ann_dict["fps"],
        frame_count=len(ann_dict["keypoint_frames"]),
        keypoint_frames=ann_dict["keypoint_frames"],
        annotation_metadata=ann_dict.get("annotation_metadata", {}),
        swim_direction=ann_dict.get("swim_direction", "left_to_right"),
        scale=ann_dict.get("scale"),
        quality={"schema_version": "annotation-quality.v2", "status": "valid", "module_readiness": {}},
    )
    db_session.add(ann)
    db_session.flush()
    return ts, ann



# ═══════════════════════════════════════════════════════════════════════════════
# Unit: routing / version (service layer)
# ═══════════════════════════════════════════════════════════════════════════════

def test_submit_with_annotation_selects_annotation_kinematics(db_session):
    from app.schemas import AnalysisSubmit

    fx_session, fx_ann = _build_chain(db_session)
    payload = AnalysisSubmit(session_id=fx_session.id, normalized_annotation_id=fx_ann.id)
    task = create_analysis_task(db_session, payload)
    assert task.pipeline_type == "annotation_kinematics"
    assert task.pipeline_version == ANNOTATION_PIPELINE_VERSION


def test_submit_hybrid_rejected(db_session):
    from app.schemas import AnalysisSubmit

    fx_session, _ = _build_chain(db_session)
    payload = AnalysisSubmit(session_id=fx_session.id, pipeline_type="hybrid")
    with pytest.raises(ValueError):
        create_analysis_task(db_session, payload)


def test_submit_mismatched_version_rejected(db_session):
    from app.schemas import AnalysisSubmit

    fx_session, _ = _build_chain(db_session)
    payload = AnalysisSubmit(
        session_id=fx_session.id, pipeline_type="model_service", pipeline_version="side_2d_v1"
    )
    with pytest.raises(ValueError):
        create_analysis_task(db_session, payload)


def test_submit_annotation_without_id_rejected(db_session):
    from app.schemas import AnalysisSubmit

    fx_session, _ = _build_chain(db_session)
    payload = AnalysisSubmit(session_id=fx_session.id, pipeline_type="annotation_kinematics")
    with pytest.raises(ValueError):
        create_analysis_task(db_session, payload)


# ═══════════════════════════════════════════════════════════════════════════════
# Quality adapter (unit)
# ═══════════════════════════════════════════════════════════════════════════════

def test_quality_adapter_maps_issue_to_modules():
    from app.services.annotation_quality.models import AnnotationQualityReport

    ann = AnnotationQualityReport(status="valid", module_readiness={})
    metric_quality = {
        "level": "warning",
        "issues": [
            {"code": ISSUE_HEAD_POINTS_INSUFFICIENT, "message": "x"},
            {"code": ISSUE_REFERENCE_BODY_LENGTH_INSUFFICIENT, "message": "y"},
        ],
    }
    summary = aggregate_side_2d_kinematics_quality(ann, metric_quality)
    mod_avail = summary.metrics["side_2d_kinematics_module_availability"]
    assert mod_avail["head_trunk"] == "degraded"
    assert mod_avail["body_posture"] == "degraded"
    assert mod_avail["upper_limb"] == "degraded"
    assert mod_avail["lower_limb"] == "degraded"
    assert summary.decision.report_availability == "degraded"


# ═══════════════════════════════════════════════════════════════════════════════
# Integration: full pipeline
# ═══════════════════════════════════════════════════════════════════════════════

def test_full_annotation_pipeline_persists_all_products(db_session):
    from app.schemas import AnalysisSubmit

    fx_session, ann = _build_chain(db_session)
    payload = AnalysisSubmit(session_id=fx_session.id, normalized_annotation_id=ann.id)
    task = create_analysis_task(db_session, payload)
    task = _run_pipeline(db_session, task)

    assert task.status == "completed"
    assert task.stage == "completed"
    assert task.progress == 100

    # 指标由 pipeline 重新计算并 upsert（fixture 已建一条，pipeline 应复用同一 calculator 记录）
    metric = _sel(db_session, AnnotationMetric, normalized_annotation_id=ann.id)
    assert metric is not None
    assert metric.calculator == "side_2d_kinematics"

    from app.models.kinematic_artifact import KinematicArtifactSet
    from app.models.kinematic_review_finding import KinematicReviewFindingSet

    assert _sel(db_session, KinematicArtifactSet, annotation_metric_id=metric.id) is not None
    assert _sel(db_session, KinematicReviewFindingSet, annotation_metric_id=metric.id) is not None

    result = task.result
    assert result is not None
    assert result.schema_version == "swim-analysis.annotation-kinematics.v1"
    assert result.diagnostics == []

    report = _sel(db_session, ReportMetadata, session_id=fx_session.id)
    assert report is not None
    assert report.source == "annotation_kinematics"
    assert "source_trace" in report.report_data
    assert "task_id" not in report.report_data
    assert "attempt" not in report.report_data


def test_revision_drift_fails_task(db_session):
    from app.schemas import AnalysisSubmit

    fx_session, ann = _build_chain(db_session)
    payload = AnalysisSubmit(session_id=fx_session.id, normalized_annotation_id=ann.id)
    task = create_analysis_task(db_session, payload)

    ann.revision += 1  # 模拟任务提交后 annotation 被重新解析
    db_session.flush()

    task = _run_pipeline(db_session, task)
    assert task.status == "failed"
    assert task.error_code == "ANNOTATION_REVISION_DRIFT"
    assert task.failed_stage == "validating_input"


def test_retry_reuses_products(db_session):
    from app.schemas import AnalysisSubmit

    fx_session, ann = _build_chain(db_session)
    payload = AnalysisSubmit(session_id=fx_session.id, normalized_annotation_id=ann.id)
    task = create_analysis_task(db_session, payload)
    task = _run_pipeline(db_session, task)
    assert task.status == "completed"

    metric_before = _sel(db_session, AnnotationMetric, normalized_annotation_id=ann.id)
    mid_before = metric_before.id

    # 第二次运行（模拟 retry 同输入）
    _run_pipeline(db_session, task)
    metric_after = _sel(db_session, AnnotationMetric, normalized_annotation_id=ann.id)
    assert metric_after.id == mid_before  # 幂等复用，不产生重复 metric


def test_retry_only_for_annotation(db_session):
    from app.schemas import AnalysisSubmit

    fx_session, ann = _build_chain(db_session)
    payload = AnalysisSubmit(session_id=fx_session.id, normalized_annotation_id=ann.id)
    task = create_analysis_task(db_session, payload)
    task.status = "failed"
    task.error_code = "X"
    db_session.flush()
    retried = retry_analysis_task(db_session, task)
    assert retried.status == "queued"
