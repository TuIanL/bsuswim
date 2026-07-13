"""Unit tests for the Kinovea annotation parser (pure functions, no DB).

Run with:  cd backend && python -m pytest tests/test_kinovea_parser.py -v
Requires: pip install pytest
"""
from pathlib import Path

import pytest

from app.services.parsers import (
    KinoveaParseError,
    parse_kinovea_csv,
    parse_kinovea_json,
    resolve_time_sec,
)

SAMPLES_DIR = Path(__file__).resolve().parent.parent / "samples"
JSON_SAMPLE = SAMPLES_DIR / "kinovea-side-freestyle.json"
CSV_SAMPLE = SAMPLES_DIR / "kinovea-side-freestyle.csv"

CSV_HEADER = "type,name,label,frame,time_sec,side,point,x,y,tag,severity,comment"


def _write_csv(tmp_path, body: str) -> str:
    p = tmp_path / "annot.csv"
    p.write_text(CSV_HEADER + "\n" + body, encoding="utf-8")
    return str(p)


# ── 7.1: valid Kinovea JSON ──


def test_parse_valid_json():
    parsed = parse_kinovea_json(str(JSON_SAMPLE))
    assert len(parsed.events) == 5
    assert len(parsed.keypoint_frames) == 2
    assert len(parsed.trajectories) == 1
    assert len(parsed.manual_tags) == 2
    assert parsed.fps == 60
    assert parsed.frame_count == 5400
    assert parsed.scale is not None
    assert parsed.warnings == []


# ── 7.2: valid Kinovea CSV ──


def test_parse_valid_csv():
    parsed = parse_kinovea_csv(str(CSV_SAMPLE), fallback_fps=60)
    assert len(parsed.events) == 5
    assert len(parsed.keypoint_frames) == 2
    assert len(parsed.trajectories) == 1
    assert len(parsed.manual_tags) == 2
    assert parsed.warnings == []


# ── 7.3: CSV keypoint rows aggregated by frame ──


def test_csv_keypoint_aggregation():
    parsed = parse_kinovea_csv(str(CSV_SAMPLE), fallback_fps=60)
    frames = sorted(kf.frame for kf in parsed.keypoint_frames)
    assert frames == [120, 240]
    kf120 = next(kf for kf in parsed.keypoint_frames if kf.frame == 120)
    assert set(kf120.points.keys()) == {
        "right_shoulder", "right_elbow", "right_wrist",
        "right_hip", "right_knee", "right_ankle",
    }


# ── 7.4: time_sec inferred from frame/fps ──


def test_time_sec_inferred_from_frame_fps(tmp_path):
    body = (
        "event,e1,入水,100,1.667,right,,,,,,\n"
        "keypoint,,,120,,right,right_shoulder,512,240,,,\n"
    )
    parsed = parse_kinovea_csv(_write_csv(tmp_path, body), fallback_fps=60)
    kf = parsed.keypoint_frames[0]
    assert kf.frame == 120
    assert kf.time_sec == pytest.approx(2.0)  # 120 / 60


def test_resolve_time_sec_helper():
    assert resolve_time_sec({"time_sec": "3.5"}, None) == 3.5
    assert resolve_time_sec({"frame": "180"}, 60) == pytest.approx(3.0)
    with pytest.raises(KinoveaParseError):
        resolve_time_sec({"frame": "10"}, None)


# ── 7.5: missing fps and no fallback → KinoveaParseError ──


def test_csv_missing_fps_no_fallback_raises(tmp_path):
    body = (
        "event,e1,入水,100,1.0,right,,,,,,\n"
        "keypoint,,,120,,right,right_shoulder,512,240,,,\n"
    )
    with pytest.raises(KinoveaParseError):
        parse_kinovea_csv(_write_csv(tmp_path, body))  # no fallback_fps


# ── 7.6: non-numeric coordinate → KinoveaParseError ──


def test_csv_non_numeric_coord_raises(tmp_path):
    body = (
        "event,e1,入水,100,1.0,right,,,,,,\n"
        "keypoint,,,120,2.0,right,right_shoulder,abc,240,,,\n"
    )
    with pytest.raises(KinoveaParseError):
        parse_kinovea_csv(_write_csv(tmp_path, body), fallback_fps=60)


# ── 7.7: Chinese point name mapped to standard ──


def test_csv_chinese_point_name_mapped(tmp_path):
    body = "keypoint,,,120,2.0,right,肩,512,240,,,\n"
    parsed = parse_kinovea_csv(_write_csv(tmp_path, body), fallback_fps=60)
    assert "right_shoulder" in parsed.keypoint_frames[0].points


# ── 7.8: missing hand_entry → semantic warning ──


def test_missing_recommended_event_warning(tmp_path):
    body = (
        "event,catch_start,抱水开始,150,2.5,right,,,,,,\n"
        "event,pull_end,推水结束,240,4.0,right,,,,,,\n"
    )
    parsed = parse_kinovea_csv(_write_csv(tmp_path, body), fallback_fps=60)
    assert any("hand_entry" in w for w in parsed.warnings)


def test_all_recommended_events_no_warning(tmp_path):
    body = (
        "event,hand_entry,入水,120,2.0,right,,,,,,\n"
        "event,catch_start,抱水开始,150,2.5,right,,,,,,\n"
        "event,pull_end,推水结束,240,4.0,right,,,,,,\n"
        "event,cycle_start,划水周期开始,120,2.0,right,,,,,,\n"
        "event,cycle_end,划水周期结束,360,6.0,right,,,,,,\n"
    )
    parsed = parse_kinovea_csv(_write_csv(tmp_path, body), fallback_fps=60)
    assert parsed.warnings == []


# ── 7.9: CSV missing required column → KinoveaParseError ──


def test_csv_missing_required_column_raises(tmp_path):
    # header without the required "x" column
    p = tmp_path / "bad.csv"
    p.write_text(
        "type,name,label,frame,time_sec,side,point,y,tag,severity,comment\n"
        "event,e1,入水,100,1.0,right,,,,,,\n",
        encoding="utf-8",
    )
    with pytest.raises(KinoveaParseError):
        parse_kinovea_csv(str(p), fallback_fps=60)
