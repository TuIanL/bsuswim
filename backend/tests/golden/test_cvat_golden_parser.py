"""Golden CVAT XML parser tests (tasks 3.1-3.7).

Validates the real CVAT 1.1 annotations.xml through the parser without
requiring a running database or API server.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.services.parsers.cvat_xml import parse_cvat_xml

FIXTURE_DIR = Path(__file__).resolve().parent.parent.parent / "tests" / "fixtures" / "kinematics_golden_v1"


def _load_manifest() -> dict:
    with open(FIXTURE_DIR / "fixture_manifest.json", "r") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def manifest() -> dict:
    return _load_manifest()


@pytest.fixture(scope="module")
def parsed(manifest: dict):
    xml_path = FIXTURE_DIR / manifest["annotations"]["relative_path"]
    return parse_cvat_xml(str(xml_path))


class TestGoldenCVATParsing:
    """3.1-3.7: CVAT parser validation against real golden XML."""

    def test_parser_produces_frames(self, parsed):
        """3.1: Parser produces non-empty keypoint frames from real XML."""
        assert len(parsed.raw_keypoint_frames) > 0, "Parser produced zero frames"

    def test_active_frames_count(self, parsed, manifest):
        """3.3: Active annotated frames count matches manifest."""
        expected = manifest["annotations"]["active_frames"]
        actual = len(parsed.raw_keypoint_frames)
        assert actual == expected, f"Expected {expected} active frames, got {actual}"

    def test_frame_range(self, parsed, manifest):
        """3.4: Annotation frame range matches manifest."""
        expected_range = manifest["annotations"]["annotation_frame_range"]
        actual_range = [f.annotation_frame for f in parsed.raw_keypoint_frames]
        assert min(actual_range) == expected_range[0], (
            f"Min frame {min(actual_range)} != {expected_range[0]}"
        )
        assert max(actual_range) == expected_range[1], (
            f"Max frame {max(actual_range)} != {expected_range[1]}"
        )

    def test_joint_count_per_frame(self, parsed, manifest):
        """3.5: Each frame has the expected number of joints."""
        expected_count = manifest["annotations"]["joint_count"]
        for f in parsed.raw_keypoint_frames:
            assert len(f.points) == expected_count, (
                f"Frame {f.annotation_frame} has {len(f.points)} joints, expected {expected_count}"
            )

    def test_joint_schema(self, parsed):
        """3.5: Joint names match COCO17 schema."""
        expected = {
            "nose", "left_eye", "right_eye", "left_ear", "right_ear",
            "left_shoulder", "right_shoulder",
            "left_elbow", "right_elbow",
            "left_wrist", "right_wrist",
            "left_hip", "right_hip",
            "left_knee", "right_knee",
            "left_ankle", "right_ankle",
        }
        for f in parsed.raw_keypoint_frames:
            actual = set(f.points.keys())
            assert actual == expected, (
                f"Frame {f.annotation_frame} joint schema mismatch: "
                f"missing={expected - actual}, extra={actual - expected}"
            )

    def test_baseline_visibility_visible(self, parsed):
        """3.6: All baseline keypoints have visibility != missing."""
        for f in parsed.raw_keypoint_frames:
            for name, pt in f.points.items():
                assert pt.visibility != "missing", (
                    f"Frame {f.annotation_frame}.{name} is missing in baseline"
                )

    def test_no_duplicate_frames(self, parsed):
        """3.7: No duplicate active frames from all-outside track termination."""
        frames = [f.annotation_frame for f in parsed.raw_keypoint_frames]
        assert len(frames) == len(set(frames)), "Duplicate annotation frames found"

    def test_native_metadata(self, parsed):
        """3.2/3.10: Native metadata contains expected structure."""
        meta = parsed.native_metadata
        assert "version" in meta
        assert "parsed_frame_count" in meta
        assert meta["parsed_frame_count"] == len(parsed.raw_keypoint_frames)
