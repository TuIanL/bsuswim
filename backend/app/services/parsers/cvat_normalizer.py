from __future__ import annotations

from app.schemas.normalized_annotation import (
    FrameMapping,
    FrameMappingEntry,
    KeypointFrame,
    KeypointPoint,
    RawCvatKeypointFrame,
)


class CvatAnnotationNormalizer:

    @staticmethod
    def normalize(
        raw_frames: list[RawCvatKeypointFrame],
        mapping: FrameMapping,
        fps_verified: bool = False,
    ) -> list[KeypointFrame]:
        mapping_index: dict[int, FrameMappingEntry] = {}
        if mapping.entries:
            for entry in mapping.entries:
                mapping_index[entry.annotation_frame] = entry

        result: list[KeypointFrame] = []
        for raw in raw_frames:
            af = raw.annotation_frame
            map_entry = mapping_index.get(af)

            source_video_frame: int | None = None
            timestamp_sec: float | None = None
            image_name: str | None = None

            if map_entry is not None:
                image_name = map_entry.image_name
                if map_entry.timestamp_sec is not None:
                    source_video_frame = map_entry.source_video_frame
                    timestamp_sec = map_entry.timestamp_sec
                elif map_entry.source_video_frame is not None:
                    source_video_frame = map_entry.source_video_frame
                    if mapping.verified and fps_verified and mapping.video_fps:
                        timestamp_sec = round(
                            source_video_frame / mapping.video_fps, 4
                        )
            elif mapping.mode == "affine" and mapping.verified:
                offset = mapping.source_frame_offset or 0
                stride = mapping.source_frame_stride or 1
                source_video_frame = offset + af * stride
                if fps_verified and mapping.video_fps:
                    timestamp_sec = round(source_video_frame / mapping.video_fps, 4)
            elif mapping.mode == "identity" and mapping.verified:
                source_video_frame = af
                if fps_verified and mapping.video_fps:
                    timestamp_sec = round(af / mapping.video_fps, 4)

            points: dict[str, KeypointPoint] = {}
            for pname, rp in raw.points.items():
                if rp.visibility == "missing":
                    points[pname] = KeypointPoint(
                        x=None, y=None,
                        visibility="missing",
                        confidence=None,
                    )
                else:
                    points[pname] = KeypointPoint(
                        x=rp.x, y=rp.y,
                        visibility=rp.visibility,
                        confidence=None,
                    )

            kf = KeypointFrame(
                frame=af,
                time_sec=timestamp_sec if timestamp_sec is not None else 0.0,
                annotation_frame=af,
                source_video_frame=source_video_frame,
                timestamp_sec=timestamp_sec,
                image_name=image_name,
                points=points,
                source_track_ids=raw.source_track_ids,
            )
            result.append(kf)

        return result
