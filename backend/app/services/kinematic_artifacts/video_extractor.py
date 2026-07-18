"""Video frame extraction with exact-frame guarantees.

The extractor returns the actually-decoded frame index so callers can verify
an exact match (critical for report evidence on long-GOP videos).
"""

from dataclasses import dataclass

import cv2
import numpy as np

from app.services.kinematic_artifacts.constants import SkipReason


@dataclass
class ExtractedFrame:
    requested_frame: int
    decoded_frame: int
    exact_match: bool
    image: np.ndarray  # BGR


class VideoFrameExtractor:
    """OpenCV-backed extractor that reads individual frames without loading
    the whole video into memory."""

    def __init__(self, video_path: str) -> None:
        self.video_path = video_path
        self._cap = cv2.VideoCapture(video_path)
        if not self._cap.isOpened():
            raise FileNotFoundError(f"cannot open video: {video_path}")
        self.frame_count = int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT))

    def extract(self, source_frame: int) -> ExtractedFrame:
        if source_frame < 0 or source_frame >= self.frame_count:
            raise IndexError(f"frame {source_frame} out of range")
        self._cap.set(cv2.CAP_PROP_POS_FRAMES, source_frame)
        ok, image = self._cap.read()
        if not ok or image is None:
            raise RuntimeError(f"decode failed at frame {source_frame}")
        decoded = int(self._cap.get(cv2.CAP_PROP_POS_FRAMES)) - 1
        return ExtractedFrame(
            requested_frame=source_frame,
            decoded_frame=decoded,
            exact_match=(decoded == source_frame),
            image=image,
        )

    def extract_many(self, source_frames: list[int]) -> dict[int, ExtractedFrame]:
        """Extract multiple frames; cache by source frame, decode in sorted order."""
        out: dict[int, ExtractedFrame] = {}
        for sf in sorted(set(source_frames)):
            out[sf] = self.extract(sf)
        return out

    def close(self) -> None:
        if self._cap is not None:
            self._cap.release()

    def __enter__(self) -> "VideoFrameExtractor":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
