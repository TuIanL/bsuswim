from __future__ import annotations

from typing import Any

from app.schemas.normalized_annotation import KeypointFrame, Trajectory
from app.services.annotation_derivation.trajectory_builder import TrajectoryBuilder
from app.services.annotation_derivation.body_center_builder import BodyCenterBuilder
from app.services.annotation_derivation.visibility_summary import VisibilitySummary


class AnnotationDerivedDataBuilder:

    @staticmethod
    def build(
        keypoint_frames: list[KeypointFrame],
        native_trajectories: list[Trajectory] | None = None,
    ) -> dict[str, Any]:
        result: dict[str, Any] = {
            "trajectories": [],
            "body_centers": [],
            "visibility_summary": {},
            "warnings": [],
        }

        try:
            trajectories = TrajectoryBuilder.build(keypoint_frames, native_trajectories)
            result["trajectories"] = [t.model_dump() for t in trajectories]
        except Exception as exc:
            result["warnings"].append(f"trajectory_builder_failed: {exc}")

        try:
            centers = BodyCenterBuilder.build(keypoint_frames)
            result["body_centers"] = [c.model_dump() for c in centers]
        except Exception as exc:
            result["warnings"].append(f"body_center_builder_failed: {exc}")

        try:
            summary = VisibilitySummary.build(keypoint_frames)
            result["visibility_summary"] = summary
        except Exception as exc:
            result["warnings"].append(f"visibility_summary_failed: {exc}")

        return result
