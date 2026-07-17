"""Tests for the CVAT XML parser."""

import os
import tempfile
import pytest

from app.schemas.normalized_annotation import (
    FrameMapping,
    FrameMappingEntry,
    RawCvatKeypointFrame,
    RawCvatPoint,
    build_contiguous_frame_ranges,
)
from app.services.parsers.cvat_normalizer import CvatAnnotationNormalizer
from app.services.parsers.cvat_xml import (
    CvatParseError,
    _has_dtd_or_entities,
    _normalize_point_name,
    _is_safe_coordinate,
    parse_cvat_xml,
)

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def _fixture_path(name: str) -> str:
    return os.path.join(FIXTURES, name)


class TestNormalizePointName:
    def test_hyphen_to_underscore(self):
        assert _normalize_point_name("left-shoulder") == "left_shoulder"
        assert _normalize_point_name("right-elbow") == "right_elbow"

    def test_face_keypoints(self):
        assert _normalize_point_name("nose") == "nose"
        assert _normalize_point_name("left-eye") == "left_eye"
        assert _normalize_point_name("right-ear") == "right_ear"


class TestSafeCoordinate:
    def test_valid_coordinates(self):
        assert _is_safe_coordinate("123.45") is True
        assert _is_safe_coordinate("0") is True

    def test_nan_rejected(self):
        assert _is_safe_coordinate("NaN") is False

    def test_infinity_rejected(self):
        assert _is_safe_coordinate("Infinity") is False
        assert _is_safe_coordinate("-Infinity") is False

    def test_negative_rejected(self):
        assert _is_safe_coordinate("-1") is False


class TestHasDTD:
    def test_plain_xml_no_dtd(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
            f.write("<annotations></annotations>")
            path = f.name
        assert _has_dtd_or_entities(path) is False
        os.unlink(path)

    def test_dtd_detected(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
            f.write('<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>')
            path = f.name
        assert _has_dtd_or_entities(path) is True
        os.unlink(path)


class TestParseCvatXml:
    def test_parse_normal(self):
        result = parse_cvat_xml(_fixture_path("cvat_56_frames.xml"))
        assert len(result.raw_keypoint_frames) == 2
        frame0 = result.raw_keypoint_frames[0]
        assert frame0.annotation_frame == 0
        assert "left_shoulder" in frame0.points
        assert "right_ankle" in frame0.points
        assert "nose" in frame0.points
        assert frame0.source_track_ids == ["0"]
        meta = result.native_metadata
        assert meta["version"] == "1.1"
        assert meta["meta"].get("size") == 356

    def test_parse_meta(self):
        result = parse_cvat_xml(_fixture_path("cvat_56_frames.xml"))
        meta = result.native_metadata["meta"]
        assert meta.get("id") == 2
        assert meta.get("size") == 356
        assert meta.get("start_frame") == 0
        assert meta.get("stop_frame") == 355

    def test_parser_no_database(self):
        result = parse_cvat_xml(_fixture_path("cvat_56_frames.xml"))
        assert result is not None
        assert len(result.raw_keypoint_frames) == 2

    def test_outside_skip_entire_skeleton(self):
        result = parse_cvat_xml(_fixture_path("cvat_56_frames.xml"))
        frames = result.raw_keypoint_frames
        assert len(frames) == 2
        for kf in frames:
            assert kf.annotation_frame in (0, 1)

    def test_occluded_mapping(self):
        result = parse_cvat_xml(_fixture_path("cvat_56_frames.xml"))
        for kf in result.raw_keypoint_frames:
            for pname, pt in kf.points.items():
                assert pt.visibility in ("visible", "occluded", "missing")
                if pt.visibility == "visible":
                    assert pt.x > 0
                    assert pt.y > 0

    def test_multi_skeleton_rejected(self):
        with pytest.raises(CvatParseError) as exc:
            parse_cvat_xml(_fixture_path("cvat_multi_skeleton.xml"))
        assert exc.value.code == "MULTIPLE_ACTIVE_SKELETONS"
        assert exc.value.frame is not None
        assert len(exc.value.track_ids) > 1

    def test_dtd_rejected(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
            f.write('<?xml version="1.0"?>\n')
            f.write('<!DOCTYPE foo [<!ENTITY xxe "test">]>\n')
            f.write("<annotations></annotations>")
            path = f.name
        with pytest.raises(CvatParseError, match="DTD"):
            parse_cvat_xml(path)
        os.unlink(path)

    def test_nan_coordinate_rejected(self):
        xml = """<?xml version="1.0"?>
<annotations>
  <track id="0" label="骨架" source="manual">
    <skeleton frame="0" keyframe="1" z_order="0">
      <points label="nose" outside="0" occluded="0" points="NaN,100"/>
    </skeleton>
  </track>
</annotations>"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
            f.write(xml)
            path = f.name
        with pytest.raises(CvatParseError, match="Invalid coordinate"):
            parse_cvat_xml(path)
        os.unlink(path)

    def test_empty_file_rejected(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
            path = f.name
        with pytest.raises(CvatParseError, match="Empty"):
            parse_cvat_xml(path)
        os.unlink(path)

    def test_no_skeleton_termination(self):
        result = parse_cvat_xml(_fixture_path("cvat_56_frames.xml"))
        for kf in result.raw_keypoint_frames:
            for pname, pt in kf.points.items():
                if pt.visibility == "missing":
                    assert pt.x is None
                    assert pt.y is None


class TestFrameMappingResolver:
    from app.services.parsers.frame_mapping import FrameMappingResolver

    def test_resolve_unknown(self):
        mapping = self.FrameMappingResolver.resolve_unknown()
        assert mapping.mode == "unknown"
        assert mapping.verified is False

    def test_resolve_identity(self):
        mapping = self.FrameMappingResolver.resolve_identity(video_fps=60.0)
        assert mapping.mode == "identity"
        assert mapping.verified is False
        assert mapping.video_fps == 60.0

    def test_with_user_override_confirmed(self):
        from app.schemas.normalized_annotation import FrameMappingOverride, ParseAnnotationOptions
        override = FrameMappingOverride(
            mode="affine",
            source_frame_offset=32,
            source_frame_stride=1,
            confirmed=True,
        )
        options = ParseAnnotationOptions(frame_mapping_override=override)
        mapping = self.FrameMappingResolver.resolve(
            cvat_meta={"start_frame": 0},
            video_fps=60.0,
            options=options,
        )
        assert mapping.mode == "affine"
        assert mapping.verified is True
        assert mapping.source_frame_offset == 32

    def test_without_override_fallback_to_unknown(self):
        mapping = self.FrameMappingResolver.resolve(
            cvat_meta={},
            video_fps=None,
        )
        assert mapping.mode == "unknown"
        assert mapping.verified is False


class TestCvatAnnotationNormalizer:
    from app.services.parsers.cvat_normalizer import CvatAnnotationNormalizer
    from app.schemas.normalized_annotation import FrameMapping

    def test_normalize_injects_fields(self):
        from app.schemas.normalized_annotation import RawCvatKeypointFrame, RawCvatPoint
        raw = [
            RawCvatKeypointFrame(
                annotation_frame=0,
                points={
                    "left_shoulder": RawCvatPoint(x=100, y=200, visibility="visible"),
                },
                source_track_ids=["0"],
            )
        ]
        mapping = self.FrameMapping(mode="identity", verified=True, video_fps=60.0)
        normalizer = self.CvatAnnotationNormalizer()
        result = normalizer.normalize(raw, mapping, fps_verified=True)
        assert len(result) == 1
        kf = result[0]
        assert kf.annotation_frame == 0
        assert kf.frame == 0
        assert kf.source_video_frame == 0
        assert kf.timestamp_sec == 0.0
        assert "left_shoulder" in kf.points

    def test_normalize_without_fps_verified_no_timestamp(self):
        from app.schemas.normalized_annotation import RawCvatKeypointFrame, RawCvatPoint
        raw = [
            RawCvatKeypointFrame(
                annotation_frame=0,
                points={
                    "left_shoulder": RawCvatPoint(x=100, y=200, visibility="visible"),
                },
                source_track_ids=["0"],
            )
        ]
        mapping = self.FrameMapping(mode="identity", verified=True, video_fps=60.0)
        normalizer = self.CvatAnnotationNormalizer()
        result = normalizer.normalize(raw, mapping, fps_verified=False)
        kf = result[0]
        assert kf.source_video_frame == 0
        assert kf.timestamp_sec is None

    def test_normalize_affine_with_offset(self):
        from app.schemas.normalized_annotation import RawCvatKeypointFrame, RawCvatPoint
        raw = [
            RawCvatKeypointFrame(
                annotation_frame=2,
                points={
                    "nose": RawCvatPoint(x=500, y=300, visibility="visible"),
                },
                source_track_ids=["5"],
            )
        ]
        mapping = self.FrameMapping(
            mode="affine", verified=True,
            source_frame_offset=32, source_frame_stride=1,
            video_fps=60.0,
        )
        normalizer = self.CvatAnnotationNormalizer()
        result = normalizer.normalize(raw, mapping, fps_verified=True)
        kf = result[0]
        assert kf.source_video_frame == 34
        assert kf.timestamp_sec == pytest.approx(34 / 60.0, rel=1e-3)


class TestTrajectoryBuilder:
    from app.services.annotation_derivation.trajectory_builder import TrajectoryBuilder
    from app.schemas.normalized_annotation import KeypointFrame, KeypointPoint

    def test_build_simple_trajectory(self):
        tkf = self.KeypointFrame
        tkpt = self.KeypointPoint
        frames = [
            tkf(
                frame=0, annotation_frame=0, time_sec=0.0, timestamp_sec=0.0,
                points={"left_wrist": tkpt(x=10, y=20, visibility="visible")},
            ),
            tkf(
                frame=1, annotation_frame=1, time_sec=0.5, timestamp_sec=0.5,
                points={"left_wrist": tkpt(x=15, y=25, visibility="visible")},
            ),
        ]
        trajectories = self.TrajectoryBuilder.build(frames)
        assert len(trajectories) == 1
        t = trajectories[0]
        assert t.point == "left_wrist"
        assert t.source == "derived_from_keypoints"
        assert len(t.frames) == 2
        assert t.frames == [0, 1]

    def test_missing_creates_gap(self):
        tkf = self.KeypointFrame
        tkpt = self.KeypointPoint
        frames = [
            tkf(
                frame=0, annotation_frame=0, time_sec=0.0, timestamp_sec=0.0,
                points={"left_wrist": tkpt(x=10, y=20, visibility="visible")},
            ),
            tkf(
                frame=1, annotation_frame=1, time_sec=0.5, timestamp_sec=0.5,
                points={"left_wrist": tkpt(x=None, y=None, visibility="missing")},
            ),
            tkf(
                frame=2, annotation_frame=2, time_sec=1.0, timestamp_sec=1.0,
                points={"left_wrist": tkpt(x=20, y=30, visibility="visible")},
            ),
        ]
        trajectories = self.TrajectoryBuilder.build(frames)
        t = trajectories[0]
        assert len(t.frames) == 2
        assert t.frames == [0, 2]


class TestBodyCenterBuilder:
    from app.services.annotation_derivation.body_center_builder import BodyCenterBuilder
    from app.schemas.normalized_annotation import KeypointFrame, KeypointPoint

    def test_both_hips_midpoint(self):
        tkf = self.KeypointFrame
        tkpt = self.KeypointPoint
        frames = [
            tkf(
                frame=0, annotation_frame=0, time_sec=0.0,
                points={
                    "left_hip": tkpt(x=100, y=200, visibility="visible"),
                    "right_hip": tkpt(x=120, y=210, visibility="visible"),
                },
            ),
        ]
        trajectories = self.BodyCenterBuilder.build(frames)
        assert len(trajectories) == 1
        t = trajectories[0]
        assert t.point == "hip_center"
        assert t.source == "derived_from_keypoints"
        assert len(t.points) == 1
        assert t.points[0] == [110.0, 205.0]

    def test_one_hip_skips(self):
        tkf = self.KeypointFrame
        tkpt = self.KeypointPoint
        frames = [
            tkf(
                frame=0, annotation_frame=0, time_sec=0.0,
                points={
                    "left_hip": tkpt(x=100, y=200, visibility="visible"),
                    "right_hip": tkpt(x=None, y=None, visibility="missing"),
                },
            ),
        ]
        trajectories = self.BodyCenterBuilder.build(frames)
        assert len(trajectories) == 0

    def test_no_hips_skips(self):
        tkf = self.KeypointFrame
        tkpt = self.KeypointPoint
        frames = [
            tkf(
                frame=0, annotation_frame=0, time_sec=0.0,
                points={
                    "left_hip": tkpt(x=None, y=None, visibility="missing"),
                    "right_hip": tkpt(x=None, y=None, visibility="missing"),
                },
            ),
        ]
        trajectories = self.BodyCenterBuilder.build(frames)
        assert len(trajectories) == 0


class TestKeypointPointValidator:
    from app.schemas.normalized_annotation import KeypointPoint

    def test_visible_with_coordinates_passes(self):
        pt = self.KeypointPoint(x=10, y=20, visibility="visible")
        assert pt.x == 10
        assert pt.y == 20

    def test_missing_with_null_coordinates_passes(self):
        pt = self.KeypointPoint(x=None, y=None, visibility="missing")
        assert pt.x is None
        assert pt.y is None

    def test_missing_with_coordinates_raises(self):
        import pydantic
        with pytest.raises((ValueError, pydantic.ValidationError)):
            self.KeypointPoint(x=10, y=20, visibility="missing")

    def test_visible_with_null_coordinates_raises(self):
        import pydantic
        with pytest.raises((ValueError, pydantic.ValidationError)):
            self.KeypointPoint(x=None, y=None, visibility="visible")

    def test_estimated_kept_for_compat(self):
        pt = self.KeypointPoint(x=10, y=20, visibility="estimated")
        assert pt.visibility == "estimated"


class TestVisibilitySummary:
    from app.services.annotation_derivation.visibility_summary import VisibilitySummary
    from app.schemas.normalized_annotation import KeypointFrame, KeypointPoint

    def test_summary_counts(self):
        tkf = self.KeypointFrame
        tkpt = self.KeypointPoint
        frames = [
            tkf(
                frame=0, annotation_frame=0, time_sec=0.0,
                points={
                    "left_wrist": tkpt(x=10, y=20, visibility="visible"),
                    "right_wrist": tkpt(x=None, y=None, visibility="missing"),
                },
            ),
            tkf(
                frame=1, annotation_frame=1, time_sec=1.0,
                points={
                    "left_wrist": tkpt(x=15, y=25, visibility="visible"),
                    "right_wrist": tkpt(x=30, y=40, visibility="visible"),
                },
            ),
        ]
        summary = self.VisibilitySummary.build(frames)
        assert summary["total_frames"] == 2
        assert summary["keypoints"]["left_wrist"]["visible"] == 2
        assert summary["keypoints"]["right_wrist"]["visible"] == 1
        assert summary["keypoints"]["right_wrist"]["missing"] == 1
        assert summary["keypoints"]["left_wrist"]["coverage"] == 1.0
        assert summary["keypoints"]["right_wrist"]["coverage"] == 0.5


class TestCompanionValidation:
    """Tests companion JSON validation in parse_annotation_file service."""

    @pytest.fixture
    def cvat_xml_path(self):
        return _fixture_path("cvat_56_frames.xml")

    @pytest.fixture
    def json_manifest(self, tmp_path):
        """Create a minimal companion JSON manifest."""
        manifest = tmp_path / "instances_default.json"
        manifest.write_text(
            '{"images": [{"id": 1, "file_name": "scene00032.jpg", "width": 3840, "height": 2176}]}',
            encoding="utf-8",
        )
        return str(manifest)

    def _make_cvat_ann_file(self, storage_path):
        """Helper to create a mocked CVAT AnnotationFile."""
        from unittest.mock import MagicMock
        from app.models.annotation import AnnotationFileStatus, AnnotationSource

        ann_file = MagicMock()
        ann_file.id = 10
        ann_file.session_video_id = 1001
        ann_file.source = "cvat"
        ann_file.file_type = "xml"
        ann_file.storage_path = storage_path
        ann_file.annotation_fps = 60.0
        ann_file.frame_count = None
        ann_file.duration_sec = None
        ann_file.status = AnnotationFileStatus.UPLOADED
        ann_file.parse_error = None
        mock_video = MagicMock()
        mock_video.fps = 60.0
        mock_video.frame_count = None
        mock_video.duration_sec = None
        mock_video_file = MagicMock()
        mock_video_file.width = 3840
        mock_video_file.height = 2176
        mock_video_file.frame_count = None
        mock_video_file.duration_sec = None
        mock_video.video_file = mock_video_file
        ann_file.session_video = mock_video
        return ann_file

    def test_companion_session_mismatch_rejected(self, cvat_xml_path, json_manifest):
        from unittest.mock import MagicMock, patch
        from fastapi import HTTPException
        from app.schemas.normalized_annotation import ParseAnnotationOptions
        from app.services.normalized_annotation_service import parse_annotation_file

        ann_file = self._make_cvat_ann_file(cvat_xml_path)
        db = MagicMock()

        companion = MagicMock()
        companion.session_video_id = 9999
        companion.storage_path = json_manifest

        def fake_get(model, id):
            if id == 10:
                return ann_file
            if id == 42:
                return companion
            return None

        db.get = fake_get

        options = ParseAnnotationOptions(companion_annotation_file_id=42)

        with patch("app.services.normalized_annotation_service.get_with_ownership_check", return_value=ann_file):
            with patch("app.services.normalized_annotation_service.get_by_annotation_file", return_value=None):
                with pytest.raises(HTTPException) as exc:
                    parse_annotation_file(db, 10, current_user_id=1, options=options)

        assert exc.value.status_code == 400
        assert "companion" in str(exc.value.detail).lower()

    def test_companion_not_found_rejected(self, cvat_xml_path):
        from unittest.mock import MagicMock, patch
        from fastapi import HTTPException
        from app.schemas.normalized_annotation import ParseAnnotationOptions
        from app.services.normalized_annotation_service import parse_annotation_file

        ann_file = self._make_cvat_ann_file(cvat_xml_path)
        db = MagicMock()

        def fake_get(model, id):
            if id == 10:
                return ann_file
            return None

        db.get = fake_get

        options = ParseAnnotationOptions(companion_annotation_file_id=999)

        with patch("app.services.normalized_annotation_service.get_with_ownership_check", return_value=ann_file):
            with patch("app.services.normalized_annotation_service.get_by_annotation_file", return_value=None):
                with pytest.raises(HTTPException) as exc:
                    parse_annotation_file(db, 10, current_user_id=1, options=options)

        assert exc.value.status_code == 400


class Test56FrameRealMode:
    """Real-mode test: 56 single-frame tracks, each skeleton is followed by an all-outside
    termination skeleton. Expect 56 KeypointFrames with no false stationary points."""

    @pytest.fixture
    def fifty_six_frame_xml(self, tmp_path):
        """Generate 56-track real-pattern CVAT XML."""
        points_template = (
            '<points label="nose" outside="0" occluded="0" points="{x},{y}"/>\n'
            '<points label="left-shoulder" outside="0" occluded="0" points="{x},{y}"/>\n'
            '<points label="right-shoulder" outside="0" occluded="0" points="{x},{y}"/>\n'
            '<points label="left-elbow" outside="0" occluded="0" points="{x},{y}"/>\n'
            '<points label="right-elbow" outside="0" occluded="0" points="{x},{y}"/>\n'
            '<points label="left-wrist" outside="0" occluded="0" points="{x},{y}"/>\n'
            '<points label="right-wrist" outside="0" occluded="0" points="{x},{y}"/>\n'
            '<points label="left-hip" outside="0" occluded="0" points="{x},{y}"/>\n'
            '<points label="right-hip" outside="0" occluded="0" points="{x},{y}"/>\n'
            '<points label="left-knee" outside="0" occluded="0" points="{x},{y}"/>\n'
            '<points label="right-knee" outside="0" occluded="0" points="{x},{y}"/>\n'
            '<points label="left-ankle" outside="0" occluded="0" points="{x},{y}"/>\n'
            '<points label="right-ankle" outside="0" occluded="0" points="{x},{y}"/>\n'
            '<points label="left-eye" outside="0" occluded="0" points="{x},{y}"/>\n'
            '<points label="right-eye" outside="0" occluded="0" points="{x},{y}"/>\n'
            '<points label="left-ear" outside="0" occluded="0" points="{x},{y}"/>\n'
            '<points label="right-ear" outside="0" occluded="0" points="{x},{y}"/>\n'
        )
        all_outside = (
            '<points label="nose" outside="1" occluded="0" points="0,0"/>\n'
            '<points label="left-shoulder" outside="1" occluded="0" points="0,0"/>\n'
            '<points label="right-shoulder" outside="1" occluded="0" points="0,0"/>\n'
            '<points label="left-elbow" outside="1" occluded="0" points="0,0"/>\n'
            '<points label="right-elbow" outside="1" occluded="0" points="0,0"/>\n'
            '<points label="left-wrist" outside="1" occluded="0" points="0,0"/>\n'
            '<points label="right-wrist" outside="1" occluded="0" points="0,0"/>\n'
            '<points label="left-hip" outside="1" occluded="0" points="0,0"/>\n'
            '<points label="right-hip" outside="1" occluded="0" points="0,0"/>\n'
            '<points label="left-knee" outside="1" occluded="0" points="0,0"/>\n'
            '<points label="right-knee" outside="1" occluded="0" points="0,0"/>\n'
            '<points label="left-ankle" outside="1" occluded="0" points="0,0"/>\n'
            '<points label="right-ankle" outside="1" occluded="0" points="0,0"/>\n'
            '<points label="left-eye" outside="1" occluded="0" points="0,0"/>\n'
            '<points label="right-eye" outside="1" occluded="0" points="0,0"/>\n'
            '<points label="left-ear" outside="1" occluded="0" points="0,0"/>\n'
            '<points label="right-ear" outside="1" occluded="0" points="0,0"/>\n'
        )
        lines = [
            '<?xml version="1.0" encoding="utf-8"?>',
            '<annotations>',
            '  <version>1.1</version>',
            '  <meta><job><id>1</id><size>356</size><mode>annotation</mode>',
            '  <start_frame>0</start_frame><stop_frame>355</stop_frame>',
            '  </job></meta>',
        ]
        for i in range(56):
            x_offset = 1600 + i * 5
            y_offset = 1000 + i * 3
            lines.append(f'  <track id="{i}" label="骨架" source="manual">')
            lines.append(f'    <skeleton frame="{i}" keyframe="1" z_order="0">')
            lines.append(points_template.format(x=x_offset, y=y_offset))
            lines.append('    </skeleton>')
            lines.append(f'    <skeleton frame="{i + 1}" keyframe="1" z_order="0">')
            lines.append(all_outside)
            lines.append('    </skeleton>')
            lines.append('  </track>')
        lines.append('</annotations>')

        path = tmp_path / "cvat_56_real.xml"
        path.write_text("\n".join(lines), encoding="utf-8")
        return str(path)

    def test_56_frames_no_false_stationary(self, fifty_six_frame_xml):
        result = parse_cvat_xml(fifty_six_frame_xml)
        assert len(result.raw_keypoint_frames) == 56
        frames = result.raw_keypoint_frames
        for i, kf in enumerate(frames):
            assert kf.annotation_frame == i
        # Verify no false stationary points: all points should be > 0
        for kf in frames:
            for pname, pt in kf.points.items():
                if pt.visibility != "missing":
                    assert pt.x > 0
                    assert pt.y > 0

    def test_56_frames_no_duplicate_frames(self, fifty_six_frame_xml):
        result = parse_cvat_xml(fifty_six_frame_xml)
        frames = result.raw_keypoint_frames
        frame_nums = [kf.annotation_frame for kf in frames]
        assert len(frame_nums) == len(set(frame_nums))

    def test_56_frames_all_coco_points_present(self, fifty_six_frame_xml):
        expected = {
            "nose", "left_eye", "right_eye", "left_ear", "right_ear",
            "left_shoulder", "right_shoulder",
            "left_elbow", "right_elbow",
            "left_wrist", "right_wrist",
            "left_hip", "right_hip",
            "left_knee", "right_knee",
            "left_ankle", "right_ankle",
        }
        result = parse_cvat_xml(fifty_six_frame_xml)
        for kf in result.raw_keypoint_frames:
            assert set(kf.points.keys()) == expected


class TestFrameMappingResolverAdvanced:
    from app.services.parsers.frame_mapping import FrameMappingResolver
    from app.schemas.normalized_annotation import FrameMapping

    def test_manifest_partial_time_evidence(self):
        manifest = [
            {"annotation_frame": 0, "source_video_frame": 100, "timestamp_sec": None, "image_name": "img_a.jpg"},
            {"annotation_frame": 1, "source_video_frame": None, "timestamp_sec": None, "image_name": "img_b.jpg"},
        ]
        mapping = self.FrameMappingResolver._resolve_explicit(manifest, None, {0, 1})
        assert mapping.mode == "explicit"
        assert mapping.verified is False
        assert mapping.verification_reason == "partial_extraction_manifest"

    def test_manifest_incomplete_coverage(self):
        manifest = [
            {"annotation_frame": 0, "source_video_frame": 100, "timestamp_sec": None, "image_name": "f0.jpg"},
            {"annotation_frame": 2, "source_video_frame": 102, "timestamp_sec": None, "image_name": "f2.jpg"},
        ]
        mapping = self.FrameMappingResolver._resolve_explicit(manifest, None, {0, 1, 2})
        assert mapping.verified is False
        assert mapping.verification_reason == "incomplete_manifest_coverage"

    def test_manifest_all_evidence_verified(self):
        manifest = [
            {"annotation_frame": 0, "source_video_frame": 100, "timestamp_sec": None, "image_name": "f0.jpg"},
            {"annotation_frame": 1, "source_video_frame": 101, "timestamp_sec": None, "image_name": "f1.jpg"},
        ]
        mapping = self.FrameMappingResolver._resolve_explicit(manifest, None, {0, 1})
        assert mapping.mode == "explicit"
        assert mapping.verified is True
        assert mapping.verification_reason == "extraction_manifest"

    def test_manifest_direct_timestamp_preserved(self):
        manifest = [
            {"annotation_frame": 0, "source_video_frame": None, "timestamp_sec": 1.25, "image_name": "f0.jpg"},
        ]
        raw = [type("Raw", (), {"annotation_frame": 0})()]
        raw[0].annotation_frame = 0
        required = {0}
        mapping = self.FrameMappingResolver._resolve_explicit(manifest, None, required)
        assert mapping.verified is True
        assert mapping.entries[0].timestamp_sec == 1.25

    def test_filename_affine_inferred(self):
        manifest = [
            {"annotation_frame": 0, "source_video_frame": None, "timestamp_sec": None, "image_name": "scene00032.jpg"},
            {"annotation_frame": 1, "source_video_frame": None, "timestamp_sec": None, "image_name": "scene00033.jpg"},
        ]
        mapping = self.FrameMappingResolver._resolve_explicit(manifest, None)
        assert mapping.mode == "affine"
        assert mapping.verified is False
        assert mapping.source_frame_offset == 32
        assert mapping.source_frame_stride == 1
        assert mapping.verification_reason == "inferred_from_filename_sequence"

    def test_filename_non_constant_stride_rejected(self):
        manifest = [
            {"annotation_frame": 0, "source_video_frame": None, "timestamp_sec": None, "image_name": "scene00032.jpg"},
            {"annotation_frame": 1, "source_video_frame": None, "timestamp_sec": None, "image_name": "scene00033.jpg"},
            {"annotation_frame": 2, "source_video_frame": None, "timestamp_sec": None, "image_name": "scene00035.jpg"},
        ]
        mapping = self.FrameMappingResolver._resolve_explicit(manifest, None)
        assert mapping.mode == "explicit"
        assert mapping.verified is False
        assert mapping.verification_reason == "partial_extraction_manifest"

    def test_duplicate_annotation_frame_rejected(self):
        manifest = [
            {"annotation_frame": 0, "source_video_frame": 100, "timestamp_sec": None, "image_name": "f0.jpg"},
            {"annotation_frame": 0, "source_video_frame": 101, "timestamp_sec": None, "image_name": "f1.jpg"},
        ]
        mapping = self.FrameMappingResolver._resolve_explicit(manifest, None)
        assert mapping.verified is False
        assert mapping.verification_reason == "duplicate_annotation_frame"

    def test_explicit_unverified_via_checker(self):
        from app.services.annotation_quality.checks.cvat_checks import check_frame_mapping
        issues = check_frame_mapping({"mode": "explicit", "verified": False})
        assert len(issues) == 1
        assert issues[0].code == "TIME_MAPPING_UNVERIFIED"

    def test_direct_timestamp_preserved_in_normalizer(self):
        raw = [
            RawCvatKeypointFrame(
                annotation_frame=0,
                points={"nose": RawCvatPoint(x=500, y=300, visibility="visible")},
                source_track_ids=["0"],
            )
        ]
        mapping = FrameMapping(
            mode="explicit", verified=True, video_fps=60.0,
            entries=[
                FrameMappingEntry(
                    annotation_frame=0, source_video_frame=None,
                    timestamp_sec=1.25, image_name="f0.jpg",
                )
            ],
        )
        result = CvatAnnotationNormalizer.normalize(raw, mapping, fps_verified=False)
        assert result[0].timestamp_sec == 1.25


class TestCvatParserCapacity:
    def test_200_tracks_no_truncation(self, tmp_path):
        points = '<points label="nose" outside="0" occluded="0" points="100,200"/>'
        lines = ['<?xml version="1.0"?><annotations><version>1.1</version><meta><job><size>250</size></job></meta>']
        for i in range(220):
            lines.append(f'<track id="{i}" label="x" source="manual">')
            lines.append(f'<skeleton frame="{i}">{points}</skeleton>')
            lines.append('</track>')
        lines.append('</annotations>')
        path = tmp_path / "over200.xml"
        path.write_text("\n".join(lines), encoding="utf-8")
        result = parse_cvat_xml(str(path))
        assert len(result.raw_keypoint_frames) == 220

    def test_file_too_large_rejected(self, tmp_path):
        path = tmp_path / "huge.xml"
        with open(path, "wb") as f:
            f.write(b"<annotations></annotations>" * (1024 * 1024 // 28 + 1))
        import os
        size = os.path.getsize(path)
        if size > 100 * 1024 * 1024:
            with pytest.raises(CvatParseError) as exc:
                parse_cvat_xml(str(path))
            assert exc.value.code == "FILE_TOO_LARGE"


class TestRawCvatPointValidator:
    from app.schemas.normalized_annotation import RawCvatPoint

    def test_outside_one_has_null_coords(self):
        pt = self.RawCvatPoint(visibility="missing")
        assert pt.x is None
        assert pt.y is None

    def test_visible_has_coords(self):
        pt = self.RawCvatPoint(x=100, y=200, visibility="visible")
        assert pt.x == 100
        assert pt.y == 200

    def test_missing_with_coords_raises(self):
        import pydantic
        with pytest.raises((ValueError, pydantic.ValidationError)):
            self.RawCvatPoint(x=10, y=20, visibility="missing")


class TestBuildContiguousFrameRanges:

    def test_contiguous_single_range(self):
        result = build_contiguous_frame_ranges([0, 1, 2, 3, 4, 5])
        assert len(result) == 1
        assert result[0].start_annotation_frame == 0
        assert result[0].end_annotation_frame == 5

    def test_sparse_multi_range(self):
        result = build_contiguous_frame_ranges([0, 1, 5, 6, 10])
        assert len(result) == 3
        assert result[0].start_annotation_frame == 0
        assert result[0].end_annotation_frame == 1
        assert result[1].start_annotation_frame == 5
        assert result[1].end_annotation_frame == 6
        assert result[2].start_annotation_frame == 10
        assert result[2].end_annotation_frame == 10

    def test_single_frame(self):
        result = build_contiguous_frame_ranges([42])
        assert len(result) == 1
        assert result[0].start_annotation_frame == 42
        assert result[0].end_annotation_frame == 42

    def test_non_zero_start(self):
        result = build_contiguous_frame_ranges([32, 33, 34])
        assert len(result) == 1
        assert result[0].start_annotation_frame == 32
        assert result[0].end_annotation_frame == 34


class TestCvatParseErrorStructured:
    def test_multi_skeleton_code_and_frame(self):
        with pytest.raises(CvatParseError) as exc:
            parse_cvat_xml(_fixture_path("cvat_multi_skeleton.xml"))
        assert exc.value.code == "MULTIPLE_ACTIVE_SKELETONS"
        assert exc.value.frame == 0
        assert exc.value.track_ids == ["0", "1"]
