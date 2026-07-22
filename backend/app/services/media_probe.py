"""Probe video metadata (FPS, resolution) via ffprobe.

Used during upload so the guided Web workflow can surface a verified FPS and
resolution without relying on the compatibility default 60.0.
"""
from __future__ import annotations

import json
import shutil
import subprocess


def probe_video_metadata(storage_path: str) -> dict:
    """Return ``{"fps": float|None, "resolution": str|None, "verified": bool}``.

    Resolution is formatted as ``"<width>x<height>"``. When ffprobe is missing
    or fails, returns ``verified=False`` with ``None`` values so callers fall
    back to an explicit or user-confirmed FPS instead of a silent default.
    """
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return {"fps": None, "resolution": None, "verified": False}

    try:
        out = subprocess.run(
            [
                ffprobe,
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=width,height,r_frame_rate,avg_frame_rate",
                "-of",
                "json",
                storage_path,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (subprocess.SubprocessError, OSError):
        return {"fps": None, "resolution": None, "verified": False}

    if out.returncode != 0:
        return {"fps": None, "resolution": None, "verified": False}

    try:
        data = json.loads(out.stdout)
        streams = data.get("streams", [])
        if not streams:
            return {"fps": None, "resolution": None, "verified": False}
        stream = streams[0]
        width = stream.get("width")
        height = stream.get("height")
        resolution = f"{width}x{height}" if width and height else None
        fps = _parse_frame_rate(stream.get("avg_frame_rate") or stream.get("r_frame_rate"))
        return {"fps": fps, "resolution": resolution, "verified": fps is not None}
    except (ValueError, KeyError, TypeError):
        return {"fps": None, "resolution": None, "verified": False}


def _parse_frame_rate(value: str | None) -> float | None:
    if not value:
        return None
    try:
        if "/" in value:
            num, den = value.split("/", 1)
            den_f = float(den)
            if den_f == 0:
                return None
            return float(num) / den_f
        return float(value)
    except (ValueError, ZeroDivisionError):
        return None
