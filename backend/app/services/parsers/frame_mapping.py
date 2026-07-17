from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.normalized_annotation import (
    FrameMapping,
    FrameMappingEntry,
    FrameMappingOverride,
    ParseAnnotationOptions,
)


_FRAME_NUMBER_RE = re.compile(r"(\d+)(?=\.[^.]+$)")


class CapturedFilenameEntry(BaseModel):
    annotation_frame: int
    image_name: str
    extracted_number: int | None = None


class FrameMappingResolver:

    @staticmethod
    def resolve(
        cvat_meta: dict[str, Any],
        video_fps: float | None,
        options: ParseAnnotationOptions | None = None,
        json_manifest: list[dict[str, Any]] | None = None,
        required_annotation_frames: set[int] | None = None,
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
                json_manifest, video_fps, required_annotation_frames
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
        required_annotation_frames: set[int] | None = None,
    ) -> FrameMapping:
        entries: list[FrameMappingEntry] = []
        for item in manifest:
            af = item.get("annotation_frame")
            svf = item.get("source_video_frame")
            ts = item.get("timestamp_sec")
            img = item.get("image_name")
            if af is None:
                continue
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

        seen_annotation = set()
        for e in entries:
            if e.annotation_frame in seen_annotation:
                return FrameMapping(
                    mode="explicit",
                    verified=False,
                    verification_reason="duplicate_annotation_frame",
                    entries=entries,
                )
            seen_annotation.add(e.annotation_frame)

        if required_annotation_frames is not None:
            entry_frames = {e.annotation_frame for e in entries}
            missing = required_annotation_frames - entry_frames
            if missing:
                return FrameMapping(
                    mode="explicit",
                    verified=False,
                    verification_reason="incomplete_manifest_coverage",
                    entries=entries,
                )

        has_time_evidence = all(
            e.source_video_frame is not None or e.timestamp_sec is not None
            for e in entries
        )

        if has_time_evidence:
            return FrameMapping(
                mode="explicit",
                verified=True,
                verification_reason="extraction_manifest",
                video_fps=video_fps,
                entries=entries,
            )

        filename_result = FrameMappingResolver._try_infer_affine_from_filenames(
            entries
        )
        if filename_result:
            return filename_result

        return FrameMapping(
            mode="explicit",
            verified=False,
            verification_reason="partial_extraction_manifest",
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
    def _extract_final_numeric_token(image_name: str) -> int | None:
        match = _FRAME_NUMBER_RE.search(image_name)
        if match:
            return int(match.group(1))
        return None

    @staticmethod
    def _try_infer_affine_from_filenames(
        entries: list[FrameMappingEntry],
    ) -> FrameMapping | None:
        pairs: list[tuple[int, int]] = []

        seen_source = set()
        for e in entries:
            if e.image_name is None:
                continue
            source_num = FrameMappingResolver._extract_final_numeric_token(e.image_name)
            if source_num is None:
                return None
            if source_num in seen_source:
                return None
            seen_source.add(source_num)
            pairs.append((e.annotation_frame, source_num))

        if len(pairs) < 2:
            return None

        pairs.sort()
        annotation_delta = pairs[1][0] - pairs[0][0]
        source_delta = pairs[1][1] - pairs[0][1]

        if annotation_delta <= 0:
            return None

        if source_delta <= 0 or source_delta % annotation_delta != 0:
            return None

        stride = source_delta // annotation_delta
        offset = pairs[0][1] - pairs[0][0] * stride

        for annotation, source in pairs:
            expected = offset + annotation * stride
            if source != expected:
                return None

        return FrameMapping(
            mode="affine",
            verified=False,
            verification_reason="inferred_from_filename_sequence",
            source_frame_offset=offset,
            source_frame_stride=stride,
        )

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
