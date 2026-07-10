"""Tests for normalized annotation schema.

Run with: python -m pytest backend/tests/test_normalized_annotation.py -v
Requires: pip install pytest pytest-mock
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.deps import get_current_user
from app.db.session import get_db
from app.main import app

ROUTE = "app.api.routes.normalized_annotations"
REPO = "app.repositories.normalized_annotation_repository"
SVC = "app.services.normalized_annotation_service"


@pytest.fixture(autouse=True)
def override_auth():
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.username = "test_coach"
    mock_user.is_active = True

    async def fake_get_current_user():
        return mock_user

    def fake_get_db():
        yield MagicMock()

    app.dependency_overrides[get_current_user] = fake_get_current_user
    app.dependency_overrides[get_db] = fake_get_db
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    return TestClient(app)


# ── Quality Checker Unit Tests ──


class TestQualityChecker:
    def test_all_good(self):
        """10.1: 完整数据 → quality level = good"""
        from app.services.quality_checker import evaluate_quality

        quality = evaluate_quality(
            fps=60,
            events=[{"name": "hand_entry", "frame": 120}],
            keypoint_frames=[{
                "frame": 120,
                "points": {
                    "right_shoulder": {}, "right_elbow": {}, "right_wrist": {},
                    "right_hip": {}, "right_knee": {}, "right_ankle": {},
                }
            }],
            scale={"pixels_per_meter": 840.5},
            frame_count=5400,
        )
        assert quality.level == "good"
        assert quality.score == 100

    def test_missing_scale_warning(self):
        """10.2: 缺 scale → quality level = warning"""
        from app.services.quality_checker import evaluate_quality

        quality = evaluate_quality(
            fps=60,
            events=[{"name": "hand_entry", "frame": 120}],
            keypoint_frames=[{
                "frame": 120,
                "points": {
                    "right_shoulder": {}, "right_elbow": {}, "right_wrist": {},
                    "right_hip": {}, "right_knee": {}, "right_ankle": {},
                }
            }],
            scale=None,
        )
        assert quality.level == "warning"
        assert "speed_distance" in [m["module"] for m in quality.disabled_modules]

    def test_missing_keypoints_error(self):
        """10.3: 缺 keypoint_frames → quality level = error"""
        from app.services.quality_checker import evaluate_quality

        quality = evaluate_quality(
            fps=60,
            events=[{"name": "hand_entry", "frame": 120}],
            keypoint_frames=[],
            scale={"pixels_per_meter": 840.5},
        )
        assert quality.level == "error"

    def test_missing_fps_error(self):
        from app.services.quality_checker import evaluate_quality

        quality = evaluate_quality(
            fps=None,
            events=[{"name": "hand_entry"}],
            keypoint_frames=[{"frame": 1, "points": {"shoulder": {}}}],
        )
        assert quality.level == "error"


# ── API Integration Tests ──


def _mock_normalized_annotation():
    from app.models.normalized_annotation import NormalizedAnnotation
    from app.models import SessionVideo, ViewType

    sv = SessionVideo(id=1001, session_id=101, video_file_id=501, view_type=ViewType.SIDE)
    ann = NormalizedAnnotation(
        id=401, session_video_id=1001, annotation_file_id=None,
        revision=1, schema_version="swim-annotation.v1", source="manual_json",
        fps=60, frame_count=5400, duration_sec=90.0,
        scale={"pixels_per_meter": 840.5},
        coordinate_system={"origin": "top_left"},
        events=[{"name": "hand_entry", "frame": 120, "time_sec": 2.0, "labeled_by": "manual"}],
        keypoint_frames=[{"frame": 120, "points": {"right_shoulder": {"x": 512, "y": 240}}}],
        trajectories=[], manual_tags=[],
        quality={"level": "good", "score": 100},
        annotation_metadata={},
        created_by=1,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    ann.session_video = sv
    return ann


class TestCreateNormalizedAnnotation:
    def test_create_success(self, client):
        """10.4: JSON 创建 normalized annotation 成功"""
        mock_ann = _mock_normalized_annotation()
        with patch(f"{ROUTE}.create_normalized_annotation", return_value=mock_ann):
            response = client.post(
                "/api/v1/session-videos/1001/normalized-annotations",
                json={
                    "source": "manual_json",
                    "fps": 60,
                    "frame_count": 5400,
                    "events": [{"name": "hand_entry", "label": "入水", "frame": 120, "time_sec": 2.0, "labeled_by": "manual"}],
                    "keypoint_frames": [{"frame": 120, "time_sec": 2.0, "phase": "hand_entry", "points": {}}],
                },
            )
        assert response.status_code == 201
        data = response.json()
        assert data["id"] == 401
        assert data["schema_version"] == "swim-annotation.v1"
        assert data["quality"]["level"] == "good"


class TestGetNormalizedAnnotation:
    def test_get_detail(self, client):
        """10.5: 查询详情"""
        mock_ann = _mock_normalized_annotation()
        with patch(f"{ROUTE}.get_with_ownership_check", return_value=mock_ann):
            response = client.get("/api/v1/normalized-annotations/401")
        assert response.status_code == 200
        assert response.json()["id"] == 401

    def test_get_not_found(self, client):
        """10.5: 查询不存在的记录"""
        from fastapi import HTTPException
        with patch(f"{ROUTE}.get_with_ownership_check", side_effect=HTTPException(status_code=404, detail="标准化标注不存在")):
            response = client.get("/api/v1/normalized-annotations/99999")
        assert response.status_code == 404


class TestListNormalizedAnnotations:
    def test_list(self, client):
        """10.5: 查询列表"""
        mock_ann = _mock_normalized_annotation()
        with patch(f"{ROUTE}.list_by_session_video", return_value=[mock_ann]):
            response = client.get("/api/v1/session-videos/1001/normalized-annotations")
        assert response.status_code == 200
        assert len(response.json()) == 1


class TestParseAnnotation:
    def _result(self):
        from app.services.normalized_annotation_service import ParseAnnotationResult
        from app.schemas.normalized_annotation import ParseSummary

        return ParseAnnotationResult(
            annotation=_mock_normalized_annotation(),
            summary=ParseSummary(
                events_count=1, keypoint_frames_count=1, trajectories_count=0, manual_tags_count=0
            ),
            warnings=[],
        )

    def test_parse_skeleton(self, client):
        """parse endpoint 骨架"""
        with patch(f"{ROUTE}.parse_annotation_file", return_value=self._result()):
            response = client.post("/api/v1/annotations/301/parse")
        assert response.status_code == 201
        assert response.json()["normalized_annotation_id"] == 401

    def test_parse_status_linked(self, client):
        """parse 成功 status = parsed"""
        with patch(f"{ROUTE}.parse_annotation_file", return_value=self._result()):
            response = client.post("/api/v1/annotations/301/parse")
        assert response.status_code == 201
        assert response.json()["status"] == "parsed"

    def test_parse_not_implemented(self, client):
        """parse 对不支持类型返回错误（service 直接抛错）"""
        from fastapi import HTTPException
        with patch(f"{ROUTE}.parse_annotation_file", side_effect=HTTPException(status_code=501, detail="not implemented")):
            response = client.post("/api/v1/annotations/302/parse")
        assert response.status_code == 501


class TestParseResponseShape:
    def test_parse_response_contains_all_fields(self, client):
        """7.10: parse 成功响应含 ParseResponse 所有字段"""
        from app.services.normalized_annotation_service import ParseAnnotationResult
        from app.schemas.normalized_annotation import ParseSummary

        result = ParseAnnotationResult(
            annotation=_mock_normalized_annotation(),
            summary=ParseSummary(
                events_count=1, keypoint_frames_count=1, trajectories_count=0, manual_tags_count=0
            ),
            warnings=["缺少推荐事件: hand_entry（入水）"],
        )
        with patch(f"{ROUTE}.parse_annotation_file", return_value=result):
            response = client.post("/api/v1/annotations/301/parse")
        assert response.status_code == 201
        data = response.json()
        for field in [
            "normalized_annotation_id", "annotation_file_id", "source",
            "status", "schema_version", "revision", "summary", "quality", "warnings",
        ]:
            assert field in data
        assert data["annotation_file_id"] == 301
        assert data["source"] == "manual_json"
        assert data["status"] == "parsed"
        assert data["summary"]["events_count"] == 1
        assert data["summary"]["keypoint_frames_count"] == 1
        assert data["warnings"] == ["缺少推荐事件: hand_entry（入水）"]

    def test_parse_response_quality_shape(self, client):
        """7.11: parse 响应 quality 含 level / score"""
        from app.services.normalized_annotation_service import ParseAnnotationResult
        from app.schemas.normalized_annotation import ParseSummary

        result = ParseAnnotationResult(
            annotation=_mock_normalized_annotation(),
            summary=ParseSummary(),
            warnings=[],
        )
        with patch(f"{ROUTE}.parse_annotation_file", return_value=result):
            response = client.post("/api/v1/annotations/301/parse")
        assert response.status_code == 201
        assert response.json()["quality"]["level"] == "good"


class TestParseOwnership:
    def test_unauthorized_returns_404(self, client):
        """7.14: 无权限返回 404（ownership check 在 service 层触发）"""
        from fastapi import HTTPException

        with patch(
            "app.services.normalized_annotation_service.get_with_ownership_check",
            side_effect=HTTPException(status_code=404, detail="标注文件不存在"),
        ):
            response = client.post("/api/v1/annotations/999/parse")
        assert response.status_code == 404


class TestRevisionIncrement:
    def test_revision(self, client):
        """10.8: revision 递增"""
        from app.services.normalized_annotation_service import ParseAnnotationResult
        from app.schemas.normalized_annotation import ParseSummary

        mock_ann = _mock_normalized_annotation()
        mock_ann.revision = 2
        result = ParseAnnotationResult(annotation=mock_ann, summary=ParseSummary(), warnings=[])
        with patch(f"{ROUTE}.parse_annotation_file", return_value=result):
            response = client.post("/api/v1/annotations/301/parse")
        assert response.status_code == 201
        assert response.json()["revision"] == 2


# ── Service-level tests: status transitions (7.12 / 7.13) ──


def _fake_annotation_file(file_type: str, storage_path: str, annotation_fps=None):
    from app.models.annotation import AnnotationFileStatus

    ann_file = MagicMock()
    ann_file.id = 1
    ann_file.session_video_id = 1001
    ann_file.source.value = "kinovea"
    ann_file.file_type = file_type
    ann_file.storage_path = storage_path
    ann_file.annotation_fps = annotation_fps
    ann_file.frame_count = None
    ann_file.duration_sec = None
    ann_file.status = AnnotationFileStatus.UPLOADED
    ann_file.parse_error = None
    return ann_file


class TestParseServiceTransitions:
    def test_parse_failed_sets_status(self, tmp_path):
        """7.12: parse 失败 → annotation_files.status = parse_failed + parse_error"""
        from app.models.annotation import AnnotationFileStatus
        from fastapi import HTTPException

        from app.services.normalized_annotation_service import parse_annotation_file

        bad = tmp_path / "bad.csv"
        bad.write_text(
            "type,name,label,frame,time_sec,side,point,y,tag,severity,comment\n"
            "event,e1,入水,100,1.0,right,,,,,,\n",
            encoding="utf-8",
        )
        ann_file = _fake_annotation_file("csv", str(bad))
        db = MagicMock()
        with patch("app.services.normalized_annotation_service.get_with_ownership_check", return_value=ann_file):
            with patch("app.services.normalized_annotation_service.get_by_annotation_file", return_value=None):
                with pytest.raises(HTTPException) as exc:
                    parse_annotation_file(db, 1, current_user_id=1)
        assert exc.value.status_code == 400
        assert ann_file.status == AnnotationFileStatus.PARSE_FAILED
        assert ann_file.parse_error is not None

    def test_repeat_parse_increments_revision(self):
        """7.13: 重复 parse 同一 annotation_file → revision += 1"""
        from app.models.annotation import AnnotationFileStatus

        from app.services.normalized_annotation_service import parse_annotation_file

        csv_sample = str(Path(__file__).resolve().parent.parent / "samples" / "kinovea-side-freestyle.csv")
        ann_file = _fake_annotation_file("csv", csv_sample, annotation_fps=60)
        existing = MagicMock()
        existing.revision = 1
        db = MagicMock()
        with patch("app.services.normalized_annotation_service.get_with_ownership_check", return_value=ann_file):
            with patch("app.services.normalized_annotation_service.get_by_annotation_file", return_value=existing):
                result = parse_annotation_file(db, 1, current_user_id=1)
        assert result.annotation is existing
        assert result.annotation.revision == 2
        assert ann_file.status == AnnotationFileStatus.PARSED
