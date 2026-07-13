from __future__ import annotations

from typing import Any

from app.schemas.normalized_annotation import KeypointFrame


class VisibilitySummary:

    @staticmethod
    def build(
        keypoint_frames: list[KeypointFrame],
    ) -> dict[str, Any]:
        point_stats: dict[str, dict[str, int]] = {}
        total_frames = len(keypoint_frames)

        for kf in keypoint_frames:
            for pname, pt in kf.points.items():
                if pname not in point_stats:
                    point_stats[pname] = {"visible": 0, "occluded": 0, "missing": 0}
                v = pt.visibility
                if v in point_stats[pname]:
                    point_stats[pname][v] += 1

        summary: dict[str, Any] = {
            "total_frames": total_frames,
            "keypoints": {},
        }
        for pname in sorted(point_stats.keys()):
            stats = point_stats[pname]
            coverage = round(
                (stats["visible"] + stats["occluded"]) / total_frames, 3
            ) if total_frames > 0 else 0.0
            summary["keypoints"][pname] = {
                "visible": stats["visible"],
                "occluded": stats["occluded"],
                "missing": stats["missing"],
                "coverage": coverage,
            }

        return summary
