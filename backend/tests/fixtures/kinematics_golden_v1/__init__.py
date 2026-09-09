"""kinematics-golden.v1 fixture integrity loader.

Loads the golden fixture, validates SHA-256 checksums, and fails hard
if any file is missing or tampered with. Never falls back to synthetic data.
"""

from __future__ import annotations

import hashlib
import copy
import json
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
    def frame_mapping_path(self) -> Path:
        return self._resolve_manifest_path(self.frame_mapping["mapping_file"])

    @property
    def expected_contract_paths(self) -> dict[str, Path]:
        return {
            name: self._resolve_manifest_path(relative_path)
            for name, relative_path in self.manifest.get("expected_contracts", {}).items()
        }

    @property
    def mutation_recipe_paths(self) -> dict[str, Path]:
        return {
            name: self._resolve_manifest_path(details["recipe"])
            for name, details in self.manifest.get("mutations", {}).items()
        }

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

        self._validate_manifest()
        self._verify_file(
            "video",
            self._resolve_manifest_path(self._manifest["video"]["relative_path"]),
            self._manifest["video"]["sha256"],
        )
        self._verify_file(
            "annotations",
            self._resolve_manifest_path(self._manifest["annotations"]["relative_path"]),
            self._manifest["annotations"]["sha256"],
        )
        frame_mapping_path = self._resolve_manifest_path(
            self._manifest["frame_mapping"]["mapping_file"]
        )
        self._verify_file("frame mapping", frame_mapping_path)
        expected_contract_paths = {
            name: self._resolve_manifest_path(relative_path)
            for name, relative_path in self._manifest["expected_contracts"].items()
        }
        mutation_recipe_paths = {
            name: self._resolve_manifest_path(details["recipe"])
            for name, details in self._manifest["mutations"].items()
        }
        for name, path in expected_contract_paths.items():
            self._verify_file(f"expected contract {name}", path)
        for name, path in mutation_recipe_paths.items():
            self._verify_file(f"mutation recipe {name}", path)
        for relative_path, expected_sha256 in self._manifest.get("integrity", {}).get("files", {}).items():
            self._verify_file(
                f"integrity file {relative_path}",
                self._resolve_manifest_path(relative_path),
                expected_sha256,
            )
        self._validate_manifest_hash()
        self._validate_frame_mapping()
        self._loaded = True
        return self

    def _resolve_manifest_path(self, relative_path: str) -> Path:
        if not relative_path or Path(relative_path).is_absolute():
            raise GoldenFixtureError(f"Invalid fixture path: {relative_path!r}")
        path = (FIXTURE_DIR / relative_path).resolve()
        try:
            path.relative_to(FIXTURE_DIR.resolve())
        except ValueError as exc:
            raise GoldenFixtureError(f"Fixture path escapes fixture root: {relative_path!r}") from exc
        return path

    def _validate_manifest(self) -> None:
        required = ("profile", "version", "video", "annotations", "frame_mapping")
        missing = [key for key in required if key not in self._manifest]
        if missing:
            raise GoldenFixtureError(f"Fixture manifest missing required fields: {', '.join(missing)}")
        if self._manifest["profile"] != "kinematics-golden.v1":
            raise GoldenFixtureError(f"Unsupported fixture profile: {self._manifest['profile']!r}")
        if self._manifest["frame_mapping"].get("mode") not in {"affine", "explicit", "segmented_affine"}:
            raise GoldenFixtureError("Fixture frame_mapping.mode must be affine, explicit, or segmented_affine")
        for key in ("expected_contracts", "mutations"):
            if not isinstance(self._manifest.get(key), dict) or not self._manifest[key]:
                raise GoldenFixtureError(f"Fixture manifest requires non-empty {key}")

    def _validate_manifest_hash(self) -> None:
        declared = self._manifest.get("integrity", {}).get("manifest_sha256")
        if not isinstance(declared, str) or len(declared) != 64:
            raise GoldenFixtureError("Fixture manifest integrity.manifest_sha256 must be a SHA-256 hex digest")
        canonical = copy.deepcopy(self._manifest)
        canonical["integrity"]["manifest_sha256"] = ""
        encoded = json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        actual = hashlib.sha256(encoded).hexdigest()
        if actual != declared:
            raise GoldenFixtureError(
                f"Fixture manifest checksum mismatch: expected {declared}, actual {actual}"
            )

    def _validate_frame_mapping(self) -> None:
        mapping = self._manifest["frame_mapping"]
        mapping_path = self._resolve_manifest_path(mapping["mapping_file"])
        with mapping_path.open("r", encoding="utf-8") as f:
            try:
                mapping_data = json.load(f)
            except json.JSONDecodeError as exc:
                raise GoldenFixtureError(f"Frame mapping is invalid JSON: {exc}") from exc

        if mapping.get("mode") != mapping_data.get("mode"):
            raise GoldenFixtureError("Manifest and frame mapping modes do not match")
        entries = mapping_data.get("entries")
        if not isinstance(entries, list) or not entries:
            raise GoldenFixtureError("Explicit frame mapping must contain non-empty entries")

        expected_annotation_frames = list(range(int(self._manifest["annotations"]["total_images"])))
        actual_annotation_frames = [entry.get("annotation_frame") for entry in entries]
        if actual_annotation_frames != expected_annotation_frames:
            raise GoldenFixtureError(
                "Frame mapping annotation frames must be contiguous from 0: "
                f"expected {expected_annotation_frames[:3]}...{expected_annotation_frames[-3:]}, "
                f"got {actual_annotation_frames[:3]}...{actual_annotation_frames[-3:]}"
            )

        source_offset = int(mapping_data.get("source_original_offset", mapping.get("source_original_offset", 0)))
        for entry in entries:
            original = entry.get("source_original_frame")
            source_frame = entry.get("source_video_frame")
            if not isinstance(original, int) or not isinstance(source_frame, int):
                raise GoldenFixtureError(f"Invalid frame mapping entry: {entry!r}")
            if original - source_offset != source_frame:
                raise GoldenFixtureError(f"Frame mapping offset mismatch: {entry!r}")

        active_count = sum(bool(entry.get("has_skeleton")) for entry in entries)
        if active_count != int(self._manifest["annotations"]["active_frames"]):
            raise GoldenFixtureError(
                f"Frame mapping active count {active_count} does not match manifest "
                f"{self._manifest['annotations']['active_frames']}"
            )

    def _verify_file(self, label: str, path: Path, expected_sha256: str | None = None) -> None:
        if not path.exists():
            expected = (
                f"Expected SHA-256 {expected_sha256[:16]}... "
                if expected_sha256
                else ""
            )
            raise GoldenFixtureError(
                f"Golden fixture file missing for {label}: {path}. "
                f"{expected}Tests cannot fall back to synthetic data."
            )

        if expected_sha256 is None:
            return
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
