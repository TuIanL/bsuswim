"""Tests for video metadata probing (ffprobe wrapper)."""
import shutil
from unittest.mock import patch

from app.services.media_probe import _parse_frame_rate, probe_video_metadata


class TestParseFrameRate:
    def test_rational(self):
        assert _parse_frame_rate("60000/1001") == 59.94005994005994

    def test_simple(self):
        assert _parse_frame_rate("30") == 30.0

    def test_zero_denominator(self):
        assert _parse_frame_rate("1/0") is None

    def test_empty(self):
        assert _parse_frame_rate(None) is None
        assert _parse_frame_rate("") is None


class TestProbeFallback:
    def test_missing_ffprobe_returns_unverified(self):
        with patch("app.services.media_probe.shutil.which", return_value=None):
            result = probe_video_metadata("/nonexistent.mp4")
        assert result["verified"] is False
        assert result["fps"] is None
        assert result["resolution"] is None

    def test_invalid_file_returns_unverified(self):
        # ffprobe present but file invalid -> returncode != 0 -> unverified
        with patch("app.services.media_probe.shutil.which", return_value="/usr/bin/ffprobe"):
            with patch("subprocess.run") as run:
                run.return_value = type("R", (), {"returncode": 1, "stdout": ""})()
                result = probe_video_metadata("/invalid.mp4")
        assert result["verified"] is False
        assert result["fps"] is None
