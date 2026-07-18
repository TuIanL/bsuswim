"""Read-only adapter that builds canonical kinematic frames for the artifact
generator, reusing the exact same resolver as the side_2d_kinematics calculator.

This guarantees that hip_mid / shoulder_mid / ankle_mid used in annotated
keyframes and trajectory charts are identical to those used inside the metric
calculation (no parallel midpoint implementation).
"""

from dataclasses import dataclass
from typing import Iterable

from app.models.normalized_annotation import NormalizedAnnotation
from app.services.metrics.kinematics.frame_resolver import (
    CanonicalKinematicFrame,
    resolve_frames,
)


@dataclass
class SelectedFrame:
    artifact_metric_key: str
    annotation_frame: int
    source_video_frame: int | None
    selection_formula_id: str
    metadata: dict | None = None


class KinematicFrameSequenceProvider:
    """Builds canonical frames from a NormalizedAnnotation's keypoint_frames."""

    def build(self, annotation: NormalizedAnnotation) -> list[CanonicalKinematicFrame]:
        frames = annotation.keypoint_frames or []
        return resolve_frames(frames)

    def index_by_annotation_frame(
        self, frames: list[CanonicalKinematicFrame]
    ) -> dict[int, CanonicalKinematicFrame]:
        return {f.annotation_frame: f for f in frames if f.annotation_frame is not None}

    def by_annotation_frames(
        self, frames: list[CanonicalKinematicFrame], annotation_frames: Iterable[int]
    ) -> list[CanonicalKinematicFrame]:
        index = self.index_by_annotation_frame(frames)
        return [index[af] for af in annotation_frames if af in index]
