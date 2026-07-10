"""Integration tests — validate flow through validator, parse, and analysis gate with real DB."""

import os
import pytest
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models import (
    AnalysisTask,
    AnalysisTaskStatus,
    NormalizedAnnotation,
    SessionVideo,
    TrainingSession,
)
from app.models.annotation import AnnotationFile, AnnotationFileStatus, AnnotationSource
from app.services.annotation_quality.legacy import normalize_quality_payload
from app.services.annotation_quality.validator import AnnotationQualityValidator
from app.services.annotation_quality.provider import YamlQualityProfileProvider
from app.services.analysis_service import (
    AnnotationQualityBlockedError,
    create_analysis_task,
    _ensure_quality_gate,
)
from app.schemas.analysis import AnalysisSubmit

PROFILES_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "backend", "app", "services", "annotation_quality", "profiles")
)


def _validator():
    return AnnotationQualityValidator(YamlQualityProfileProvider(PROFILES_DIR))


class TestValidatorIntegration:
    """Validator integration: given full/warning/invalid fixtures, assert quality outcome."""

    FULL_EVENTS = [
        {"name": "hand_entry", "label": "入水", "frame": 10, "time_sec": 0.5, "side": "right"},
        {"name": "catch_start", "label": "抱水", "frame": 20, "time_sec": 1.0, "side": "right"},
        {"name": "pull_end", "label": "推水", "frame": 30, "time_sec": 1.5, "side": "right"},
        {"name": "hand_entry", "label": "入水", "frame": 50, "time_sec": 2.5, "side": "right"},
        {"name": "catch_start", "label": "抱水", "frame": 60, "time_sec": 3.0, "side": "right"},
        {"name": "pull_end", "label": "推水", "frame": 70, "time_sec": 3.5, "side": "right"},
    ]

    FULL_KEYPOINTS = [
        {
            "frame": f,
            "time_sec": f / 60.0,
            "points": {
                "shoulder": {"x": 500, "y": 200},
                "elbow": {"x": 480, "y": 300},
                "wrist": {"x": 460, "y": 400},
                "hip": {"x": 500, "y": 350},
                "knee": {"x": 490, "y": 500},
                "ankle": {"x": 480, "y": 600},
            },
        }
        for f in range(1, 60)
    ]

    FULL_SCALE = {"method": "lane_marker", "pixels_per_meter": 100.0}

    def test_full_annotation_valid(self):
        report = _validator().validate(
            events=self.FULL_EVENTS,
            keypoint_frames=self.FULL_KEYPOINTS,
            scale=self.FULL_SCALE,
            fps=60.0,
            frame_count=100,
            reference_lines={"waterline": {"points": [[0, 300], [100, 300]]}},
            swim_direction="left_to_right",
        )
        assert report.status == "valid"
        assert report.summary.blocking_count == 0
        assert report.summary.error_count == 0
        assert "body_position" in report.module_readiness
        assert report.module_readiness["body_position"].status == "ready"

    def test_missing_scale_warning(self):
        report = _validator().validate(
            events=self.FULL_EVENTS,
            keypoint_frames=self.FULL_KEYPOINTS,
            scale=None,
            fps=60.0,
            frame_count=100,
            reference_lines=None,
            swim_direction=None,
        )
        assert report.status == "warning"
        assert report.module_readiness["efficiency"].status in ("blocked", "degraded")

    def test_missing_keypoints_invalid(self):
        report = _validator().validate(
            events=self.FULL_EVENTS,
            keypoint_frames=[],
            scale=self.FULL_SCALE,
            fps=60.0,
            frame_count=100,
            reference_lines=None,
            swim_direction=None,
        )
        assert report.status == "invalid"

    def test_frame_out_of_range_invalid(self):
        bad_events = [{"name": "hand_entry", "frame": 200, "time_sec": 10.0}]
        report = _validator().validate(
            events=bad_events,
            keypoint_frames=self.FULL_KEYPOINTS,
            scale=self.FULL_SCALE,
            fps=60.0,
            frame_count=100,
            reference_lines=None,
            swim_direction=None,
        )
        assert report.status == "invalid"
        assert any(i.code == "FRAME_OUT_OF_RANGE" for i in report.issues)

    def test_non_core_blocked_still_warning(self):
        events = [{"name": "hand_entry", "frame": 10, "time_sec": 0.5, "side": "right"},
                  {"name": "hand_entry", "frame": 50, "time_sec": 2.5, "side": "right"}]
        kfs = [{"frame": f, "time_sec": f / 60.0,
                "points": {"shoulder": {"x": 500, "y": 200}, "elbow": {"x": 480, "y": 300},
                           "wrist": {"x": 460, "y": 400}, "hip": {"x": 500, "y": 350},
                           "knee": {"x": 490, "y": 500}, "ankle": {"x": 480, "y": 600},}} for f in range(1, 10)]
        report = _validator().validate(
            events=events, keypoint_frames=kfs, scale=None, fps=60.0, frame_count=100,
            reference_lines=None, swim_direction=None,
        )
        assert report.status == "warning"
        assert report.module_readiness["efficiency"].status == "blocked"


class TestQualityGate:
    """Analysis quality gate: valid → allow, invalid → block, warning → require acknowledge."""

    _QUALITY_BASE = {
        "source_revision": 1,
        "validator_version": "1.0.0",
        "profile": {"id": "side_technical_v1", "version": "1.0.0"},
        "validated_at": "2026-01-01T00:00:00+00:00",
        "summary": {"blocking_count": 0, "error_count": 0, "warning_count": 0, "info_count": 0},
        "module_readiness": {},
    }

    def _make_annotation(self, db_session: Session, sv: SessionVideo, quality: dict) -> NormalizedAnnotation:
        merged = {**self._QUALITY_BASE, **quality}
        ann = NormalizedAnnotation(
            session_video_id=sv.id,
            source="kinovea",
            fps=60.0,
            frame_count=100,
            quality=merged,
        )
        db_session.add(ann)
        db_session.flush()
        return ann

    def test_valid_annotation_allows_task(self, db_session: Session, test_session: TrainingSession, test_session_video: SessionVideo):
        ann = self._make_annotation(db_session, test_session_video, {
            "schema_version": "annotation-quality.v2",
            "status": "valid",
        })
        payload = AnalysisSubmit(session_id=test_session.id, normalized_annotation_id=ann.id)
        task = create_analysis_task(db_session, payload)
        assert task.status == AnalysisTaskStatus.QUEUED

    def test_invalid_annotation_blocks_409(self, db_session: Session, test_session: TrainingSession, test_session_video: SessionVideo):
        ann = self._make_annotation(db_session, test_session_video, {
            "schema_version": "annotation-quality.v2",
            "status": "invalid",
            "summary": {"blocking_count": 1, "error_count": 1, "warning_count": 0, "info_count": 0},
            "issues": [{"code": "FRAME_OUT_OF_RANGE", "category": "temporal", "severity": "error", "blocking": True, "message": "test"}],
            "module_readiness": {},
        })
        payload = AnalysisSubmit(session_id=test_session.id, normalized_annotation_id=ann.id)
        with pytest.raises(AnnotationQualityBlockedError):
            create_analysis_task(db_session, payload)

    def test_warning_without_acknowledge_blocks(self, db_session: Session, test_session: TrainingSession, test_session_video: SessionVideo):
        ann = self._make_annotation(db_session, test_session_video, {
            "schema_version": "annotation-quality.v2",
            "status": "warning",
        })
        payload = AnalysisSubmit(session_id=test_session.id, normalized_annotation_id=ann.id)
        with pytest.raises(AnnotationQualityBlockedError):
            create_analysis_task(db_session, payload)

    def test_warning_with_acknowledge_proceeds(self, db_session: Session, test_session: TrainingSession, test_session_video: SessionVideo):
        ann = self._make_annotation(db_session, test_session_video, {
            "schema_version": "annotation-quality.v2",
            "status": "warning",
        })
        payload = AnalysisSubmit(session_id=test_session.id, normalized_annotation_id=ann.id, acknowledge_quality_warnings=True)
        task = create_analysis_task(db_session, payload)
        assert task.status == AnalysisTaskStatus.QUEUED

    def test_revision_drift_detected(self, db_session: Session, test_session: TrainingSession, test_session_video: SessionVideo):
        ann = self._make_annotation(db_session, test_session_video, {
            "schema_version": "annotation-quality.v2",
            "status": "valid",
        })
        ann.revision = 2
        db_session.flush()
        from app.services.annotation_quality.issue_codes import ANNOTATION_REVISION_DRIFT
        with pytest.raises(AnnotationQualityBlockedError) as excinfo:
            _ensure_quality_gate(ann, revision_locked=1)
        issues = excinfo.value.quality.get("issues", [])
        assert any(i.get("code") == ANNOTATION_REVISION_DRIFT for i in issues)

    def test_task_input_locked_to_annotation(self, db_session: Session, test_session: TrainingSession, test_session_video: SessionVideo):
        ann = self._make_annotation(db_session, test_session_video, {
            "schema_version": "annotation-quality.v2",
            "status": "valid",
        })
        payload = AnalysisSubmit(session_id=test_session.id, normalized_annotation_id=ann.id)
        task = create_analysis_task(db_session, payload)
        ai = (task.request_payload or {}).get("analysis_input", {})
        assert ai.get("annotation_id") == ann.id
        assert ai.get("annotation_revision") == ann.revision
