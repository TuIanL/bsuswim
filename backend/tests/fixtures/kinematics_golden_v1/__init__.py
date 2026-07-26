"""kinematics-golden.v1 fixture integrity loader.

Loads the golden fixture, validates SHA-256 checksums, and fails hard
if any file is missing or tampered with. Never falls back to synthetic data.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

FIXTURE_DIR = Path(__file__).resolve().parent
MANIFEST_PATH = FIXTURE_DIR / "fixture_manifest.json"


class GoldenFixtureError(Exception):
    """Raised when golden fixture integrity check fails."""


class GoldenFixture:
    """Immutable golden fixture loaded from disk with integrity verification."""

    def __init__(self) -> None:
        self._manifest: dict[str, Any] = {}
        self._loaded = False

    @property
    def manifest(self) -> dict[str, Any]:
        if not self._loaded:
            raise GoldenFixtureError("Fixture not loaded. Call load() first.")
        return self._manifest

    @property
    def video_path(self) -> Path:
        return FIXTURE_DIR / self.manifest["video"]["relative_path"]

    @property
    def annotations_path(self) -> Path:
        return FIXTURE_DIR / self.manifest["annotations"]["relative_path"]

    @property
    def video_sha256(self) -> str:
        return self.manifest["video"]["sha256"]

    @property
    def annotations_sha256(self) -> str:
        return self.manifest["annotations"]["sha256"]

    @property
    def video_fps(self) -> float:
        return float(self.manifest["video"]["fps"])

    @property
    def video_fps_fraction(self) -> str:
        return self.manifest["video"]["fps_fraction"]

    @property
    def video_resolution(self) -> str:
        return self.manifest["video"]["resolution"]

    @property
    def video_width(self) -> int:
        return self.manifest["video"]["width"]

    @property
    def video_height(self) -> int:
        return self.manifest["video"]["height"]

    @property
    def video_duration_sec(self) -> float:
        return float(self.manifest["video"]["duration_sec"])

    @property
    def video_total_frames(self) -> int:
        return self.manifest["video"]["total_frames"]

    @property
    def active_frames(self) -> int:
        return self.manifest["annotations"]["active_frames"]

    @property
    def annotation_frame_range(self) -> tuple[int, int]:
        r = self.manifest["annotations"]["annotation_frame_range"]
        return (r[0], r[1])

    @property
    def frame_mapping(self) -> dict[str, Any]:
        return self.manifest["frame_mapping"]

    @property
    def joint_schema(self) -> str:
        return self.manifest["annotations"]["joint_schema"]

    @property
    def joint_count(self) -> int:
        return self.manifest["annotations"]["joint_count"]

    def load(self) -> GoldenFixture:
        """Load fixture manifest and verify all file checksums.

        Returns self for chaining.

        Raises GoldenFixtureError if:
        - Manifest is missing
        - Manifest JSON is invalid
        - Any source file is missing
        - Any source file checksum does not match manifest
        """
        if not MANIFEST_PATH.exists():
            raise GoldenFixtureError(
                f"Golden fixture manifest not found: {MANIFEST_PATH}. "
                "The kinematics-golden.v1 fixture must be present. "
                "Tests cannot fall back to synthetic data."
            )

        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            try:
                self._manifest = json.load(f)
            except json.JSONDecodeError as e:
                raise GoldenFixtureError(
                    f"Golden fixture manifest is invalid JSON: {e}"
                ) from e

        self._verify_file("video", self.video_path, self.video_sha256)
        self._verify_file("annotations", self.annotations_path, self.annotations_sha256)
        self._loaded = True
        return self

    def _verify_file(self, label: str, path: Path, expected_sha256: str) -> None:
        if not path.exists():
            raise GoldenFixtureError(
                f"Golden fixture file missing: {path}. "
                f"Expected {label} with SHA-256 {expected_sha256[:16]}... "
                "Tests cannot fall back to synthetic data."
            )

        actual = _sha256_file(path)
        if actual != expected_sha256:
            raise GoldenFixtureError(
                f"Golden fixture checksum mismatch for {label}: {path}\n"
                f"  Expected: {expected_sha256}\n"
                f"  Actual:   {actual}\n"
                "Tests cannot fall back to synthetic data."
            )


def _sha256_file(path: Path) -> str:
    """Compute SHA-256 hex digest of a file."""
    sha = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha.update(chunk)
    return sha.hexdigest()


# Singleton pattern for test convenience
_fixture: GoldenFixture | None = None


def load_golden_fixture() -> GoldenFixture:
    """Load (or return cached) golden fixture with integrity verification.

    Never falls back to synthetic data. Fixture must be present and valid.
    """
    global _fixture
    if _fixture is None:
        _fixture = GoldenFixture().load()
    return _fixture


def reset_fixture_cache() -> None:
    """Reset cached fixture (for test isolation)."""
    global _fixture
    _fixture = None
