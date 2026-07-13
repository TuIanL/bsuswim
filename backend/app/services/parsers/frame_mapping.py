from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.normalized_annotation import (
    FrameMapping,
    FrameMappingEntry,
    FrameMappingOverride,
    ParseAnnotationOptions,
)


class FrameMappingResolver:

    @staticmethod
    def resolve(
        cvat_meta: dict[str, Any],
        video_fps: float | None,
        options: ParseAnnotationOptions | None = None,
        json_manifest: list[dict[str, Any]] | None = None,
    ) -> FrameMapping:
        if options and options.frame_mapping_override:
            override = options.frame_mapping_override
            if override.confirmed:
                return FrameMapping(
                    mode=override.mode,
                    verified=True,
                    verification_reason="user_confirmed",
                    source_frame_offset=override.source_frame_offset,
                    source_frame_stride=override.source_frame_stride,
                    video_fps=video_fps,
                )
            return FrameMapping(
                mode=override.mode,
                verified=False,
                verification_reason="user_provided_not_confirmed",
                source_frame_offset=override.source_frame_offset,
                source_frame_stride=override.source_frame_stride,
                video_fps=video_fps,
            )

        if json_manifest:
            return FrameMappingResolver._resolve_explicit(
                json_manifest, video_fps
            )

        inferred = FrameMappingResolver._try_infer_affine(cvat_meta)
        if inferred:
            return inferred

        return FrameMapping(
            mode="unknown",
            verified=False,
            verification_reason="no_mapping_source_available",
        )

    @staticmethod
    def _resolve_explicit(
        manifest: list[dict[str, Any]],
        video_fps: float | None,
    ) -> FrameMapping:
        entries: list[FrameMappingEntry] = []
        for item in manifest:
            af = item.get("annotation_frame")
            svf = item.get("source_video_frame")
            ts = item.get("timestamp_sec")
            img = item.get("image_name")
            if af is None:
                continue
            if ts is None and svf is not None and video_fps:
                ts = svf / video_fps
            entries.append(FrameMappingEntry(
                annotation_frame=af,
                source_video_frame=svf,
                timestamp_sec=ts,
                image_name=img,
            ))
        if not entries:
            return FrameMapping(
                mode="unknown",
                verified=False,
                verification_reason="empty_manifest",
            )
        return FrameMapping(
            mode="explicit",
            verified=True,
            verification_reason="extraction_manifest",
            video_fps=video_fps,
            entries=entries,
        )

    @staticmethod
    def _try_infer_affine(
        cvat_meta: dict[str, Any],
    ) -> FrameMapping | None:
        start_frame = cvat_meta.get("start_frame")
        if start_frame is None:
            start_frame = 0
        if not isinstance(start_frame, int):
            return None
        if start_frame != 0:
            return FrameMapping(
                mode="affine",
                verified=False,
                verification_reason="inferred_from_meta_offset",
                source_frame_offset=start_frame,
                source_frame_stride=1,
            )
        return None

    @staticmethod
    def resolve_identity(video_fps: float | None) -> FrameMapping:
        return FrameMapping(
            mode="identity",
            verified=False,
            verification_reason="requires_user_confirmation",
            video_fps=video_fps,
        )

    @staticmethod
    def resolve_unknown() -> FrameMapping:
        return FrameMapping(
            mode="unknown",
            verified=False,
            verification_reason="no_mapping_source_available",
        )
