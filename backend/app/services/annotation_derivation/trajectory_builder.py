from __future__ import annotations

from typing import Any

from app.schemas.normalized_annotation import KeypointFrame, Trajectory


TRAJECTORY_SOURCE = "derived_from_keypoints"
BUILDER_VERSION = "1.0.0"


class TrajectoryBuilder:

    @staticmethod
    def build(
        keypoint_frames: list[KeypointFrame],
        native_trajectories: list[Trajectory] | None = None,
    ) -> list[Trajectory]:
        native_point_names: set[str] = set()
        if native_trajectories:
            for t in native_trajectories:
                if t.point:
                    native_point_names.add(t.point)

        point_names: set[str] = set()
        for kf in keypoint_frames:
            point_names.update(kf.points.keys())

        trajectories: list[Trajectory] = []
        for pname in sorted(point_names):
            if pname in native_point_names:
                continue
            traj = TrajectoryBuilder._build_single(pname, keypoint_frames)
            if traj.frames:
                trajectories.append(traj)

        return trajectories

    @staticmethod
    def _build_single(
        point_name: str,
        keypoint_frames: list[KeypointFrame],
    ) -> Trajectory:
        sorted_frames = sorted(keypoint_frames, key=lambda kf: kf.annotation_frame)
        samples: list[dict[str, Any]] = []
        for kf in sorted_frames:
            pt = kf.points.get(point_name)
            if pt is None:
                continue
            if pt.visibility == "missing":
                continue
            sample = {
                "annotation_frame": kf.annotation_frame,
                "timestamp_sec": kf.timestamp_sec,
                "x": pt.x,
                "y": pt.y,
                "visibility": pt.visibility,
            }
            samples.append(sample)

        frames = [s["annotation_frame"] for s in samples]
        points = [[s["x"], s["y"]] for s in samples]

        return Trajectory(
            name=point_name,
            label=point_name,
            point=point_name,
            frames=frames,
            points=points,
            source=TRAJECTORY_SOURCE,
        )
