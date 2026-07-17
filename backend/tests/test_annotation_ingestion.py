"""Tests for annotation ingestion workflow (change 2)."""

from unittest.mock import MagicMock

import pytest

from app.services.annotation_quality.readiness import derive_analysis_readiness
from app.schemas.annotation import (
    AnnotationFileListItem,
    AnnotationIngestResponse,
)
from app.schemas.normalized_annotation import AnalysisReadiness, ParseSummary


class TestDeriveAnalysisReadiness:

    def test_none_quality_returns_none(self):
        assert derive_analysis_readiness(None) is None

    def test_valid_quality_returns_ready(self):
        quality = {
            "schema_version": "annotation-quality.v2",
            "status": "valid",
            "summary": {"blocking_count": 0, "error_count": 0, "warning_count": 0, "info_count": 0},
            "module_readiness": {},
            "issues": [],
            "score": 100,
        }
        r = derive_analysis_readiness(quality)
        assert r.can_submit is True
        assert r.requires_acknowledgement is False

    def test_warning_quality_requires_acknowledgement(self):
        quality = {
            "schema_version": "annotation-quality.v2",
            "status": "warning",
            "summary": {"blocking_count": 0, "error_count": 0, "warning_count": 1, "info_count": 0},
            "module_readiness": {},
            "issues": [],
            "score": 80,
        }
        r = derive_analysis_readiness(quality)
        assert r.can_submit is True
        assert r.requires_acknowledgement is True

    def test_invalid_quality_blocks_submit(self):
        quality = {
            "schema_version": "annotation-quality.v2",
            "status": "invalid",
            "summary": {"blocking_count": 2, "error_count": 2, "warning_count": 0, "info_count": 0},
            "module_readiness": {},
            "issues": [],
            "score": 30,
        }
        r = derive_analysis_readiness(quality)
        assert r.can_submit is False


class TestAnnotationListHydration:

    def test_list_populates_hydrated_fields(self):
        item = AnnotationFileListItem(
            id=1, session_video_id=10, source="cvat", view_type="side",
            file_type="xml", version=1, status="parsed",
            original_filename="test.xml", annotation_fps=60.0, uploaded_at=None,
            normalized_annotation_id=42, normalized_revision=3,
            quality_status="valid",
            analysis_readiness=AnalysisReadiness(
                can_submit=True, requires_acknowledgement=False,
                blocking_issue_count=0, affected_modules=[],
            ),
            parse_warnings=[], parse_error=None,
        )
        assert item.normalized_annotation_id == 42
        assert item.normalized_revision == 3
        assert item.quality_status == "valid"
        assert item.analysis_readiness.can_submit is True

    def test_list_preserves_uploaded_records(self):
        item = AnnotationFileListItem(
            id=2, session_video_id=10, source="cvat", view_type="side",
            file_type="xml", version=1, status="uploaded",
            original_filename="pending.xml", annotation_fps=None, uploaded_at=None,
        )
        assert item.normalized_annotation_id is None
        assert item.quality_status is None

    def test_list_preserves_parse_failed_records(self):
        item = AnnotationFileListItem(
            id=3, session_video_id=10, source="cvat", view_type="side",
            file_type="xml", version=1, status="parse_failed",
            original_filename="bad.xml", annotation_fps=None, uploaded_at=None,
            parse_error="XML parse error",
        )
        assert item.status == "parse_failed"
        assert item.parse_error == "XML parse error"


class TestAnnotationIngestResponse:

    def test_response_contains_all_fields(self):
        resp = AnnotationIngestResponse(
            annotation_file_id=10, session_video_id=7,
            session_id=3, video_file_id=18,
            source="cvat", file_status="parsed", file_version=1,
            original_filename="annotations.xml",
            normalized_annotation_id=21, normalized_revision=1,
            schema_version="swim-annotation.v1",
            parse_summary=ParseSummary(
                events_count=0, keypoint_frames_count=56,
                trajectories_count=17, manual_tags_count=0,
            ),
            quality={"status": "warning"},
            analysis_readiness=AnalysisReadiness(
                can_submit=True, requires_acknowledgement=True,
                blocking_issue_count=0, affected_modules=["rhythm"],
            ),
            warnings=["仅部分视频帧存在有效骨架标注"],
        )
        assert resp.normalized_annotation_id == 21
        assert resp.normalized_annotation_id != resp.annotation_file_id

    def test_parse_success_with_invalid_quality(self):
        resp = AnnotationIngestResponse(
            annotation_file_id=11, session_video_id=7,
            session_id=3, video_file_id=18,
            source="cvat", file_status="parsed", file_version=1,
            original_filename="bad_quality.xml",
            normalized_annotation_id=22, normalized_revision=1,
            schema_version="swim-annotation.v1",
            parse_summary=ParseSummary(keypoint_frames_count=10),
            quality={"status": "invalid"},
            analysis_readiness=AnalysisReadiness(can_submit=False),
            warnings=["关键帧覆盖率过低"],
        )
        assert resp.file_status == "parsed"
        assert resp.quality["status"] == "invalid"
        assert resp.analysis_readiness.can_submit is False


class TestIngestionService:

    def test_service_imports(self):
        from app.services.annotation_ingestion_service import ingest_annotation, AnnotationIngestionResult
        assert ingest_annotation is not None
        assert AnnotationIngestionResult is not None

    def test_result_to_response(self):
        from app.services.annotation_ingestion_service import AnnotationIngestionResult
        from app.services.normalized_annotation_service import ParseAnnotationResult

        ann_file = MagicMock()
        ann_file.id = 10
        ann_file.session_video_id = 7
        ann_file.source = "cvat"
        ann_file.status = "parsed"
        ann_file.version = 1
        ann_file.original_filename = "test.xml"

        na = MagicMock()
        na.id = 21
        na.revision = 1
        na.schema_version = "swim-annotation.v1"
        na.quality = {"status": "valid"}

        parse_result = ParseAnnotationResult(
            annotation=na,
            summary=ParseSummary(keypoint_frames_count=56),
            warnings=[],
        )
        result = AnnotationIngestionResult(
            annotation_file=ann_file, parse_result=parse_result,
        )
        response = result.to_response(session_id=3, video_file_id=18)
        assert response.normalized_annotation_id == 21
        assert response.annotation_file_id == 10
        assert response.normalized_annotation_id != response.annotation_file_id


class TestAnalysisSubmissionExceptions:

    def test_exception_imports(self):
        from app.services.analysis_service import (
            AnnotationSelectionRequiredError,
            AnnotationInputUnavailableError,
        )
        err = AnnotationSelectionRequiredError(candidate_ids=[21, 24])
        assert err.candidate_ids == [21, 24]

        err2 = AnnotationInputUnavailableError(reason="NO_SUBMITTABLE_ANNOTATION")
        assert err2.reason == "NO_SUBMITTABLE_ANNOTATION"

    def test_video_only_compatibility(self):
        from app.services.analysis_service import AnnotationInputUnavailableError
        with pytest.raises(AnnotationInputUnavailableError) as exc:
            raise AnnotationInputUnavailableError(reason="NO_SUBMITTABLE_ANNOTATION")
        assert exc.value.reason == "NO_SUBMITTABLE_ANNOTATION"
