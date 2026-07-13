from __future__ import annotations

from typing import Any

from app.schemas.normalized_annotation import KeypointFrame, Trajectory


TRAJECTORY_SOURCE = "derived_from_keypoints"
BUILDER_VERSION = "1.0.0"


class BodyCenterBuilder:

    @staticmethod
    def build(
        keypoint_frames: list[KeypointFrame],
    ) -> list[Trajectory]:
        sorted_frames = sorted(keypoint_frames, key=lambda kf: kf.annotation_frame)

        hip_center_samples: list[dict[str, Any]] = []
        for kf in sorted_frames:
            left_hip = kf.points.get("left_hip")
            right_hip = kf.points.get("right_hip")
            left_visible = (
                left_hip is not None
                and left_hip.x is not None
                and left_hip.visibility != "missing"
            )
            right_visible = (
                right_hip is not None
                and right_hip.x is not None
                and right_hip.visibility != "missing"
            )

            if left_visible and right_visible:
                cx = (left_hip.x + right_hip.x) / 2.0
                cy = (left_hip.y + right_hip.y) / 2.0
                hip_center_samples.append({
                    "annotation_frame": kf.annotation_frame,
                    "timestamp_sec": kf.timestamp_sec,
                    "x": cx,
                    "y": cy,
                    "visibility": "visible",
                })

        if not hip_center_samples:
            return []

        frames = [s["annotation_frame"] for s in hip_center_samples]
        points = [[s["x"], s["y"]] for s in hip_center_samples]

        hip_trajectory = Trajectory(
            name="hip_center",
            label="髋部中点",
            point="hip_center",
            frames=frames,
            points=points,
            source=TRAJECTORY_SOURCE,
        )
        return [hip_trajectory]
