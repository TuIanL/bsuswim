"""eval_keypoints CLI 端到端测试（tasks 5.10–5.13）。"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
TOOL = BACKEND / "tools" / "eval_keypoints.py"
FIXTURE = BACKEND / "tests" / "fixtures" / "kinematics_golden_v1" / "source" / "annotations.xml"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_tool(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(TOOL), *args],
        cwd=str(BACKEND),
        capture_output=True,
        text=True,
    )


def _shift_x(node: ET.Element, shift: float) -> None:
    raw = node.get("points") or ""
    parts = [p for p in raw.split(",") if p.strip()]
    if len(parts) < 2:
        return
    parts[0] = f"{float(parts[0]) + shift:.2f}"
    node.set("points", ",".join(parts))


def make_shifted_copy(source: Path, target: Path, shift: float = 10.0, drop_frames: int = 0) -> Path:
    tree = ET.parse(str(source))
    root = tree.getroot()
    images = root.findall(".//image")
    for index, image in enumerate(images):
        if index < drop_frames:
            root.remove(image)
            continue
        for node in image.findall(".//points"):
            _shift_x(node, shift)
    tree.write(str(target), encoding="utf-8", xml_declaration=True)
    return target


@pytest.mark.skipif(not FIXTURE.is_file(), reason="缺少 golden fixture")
def test_cli_reports_pairing_and_per_joint(tmp_path: Path):
    """5.10：真实夹具作 reference，平移候选 → 配对帧与逐关节字段正确。"""
    candidate = make_shifted_copy(FIXTURE, tmp_path / "candidate.xml", shift=10.0)
    out = tmp_path / "report.json"
    md = tmp_path / "report.md"

    result = run_tool(
        "--reference", str(FIXTURE),
        "--candidate", str(candidate),
        "--format", "cvat",
        "--out", str(out),
        "--md-out", str(md),
    )
    assert result.returncode == 0, result.stderr

    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["schema_version"] == "accuracy-report.v1"
    assert report["pairing"]["paired_frames"] == 104
    assert report["pairing"]["dropped"] == 0
    assert report["params"]["area_source"] == "keypoint_bbox"
    assert report["aggregate"]["joints_evaluated"] == 17
    assert len(report["per_joint"]) == 17

    # 纯 x 平移 10px：每个关节的 rmse_px 都应为 10（腕/踝等同样平移）
    rmses = {item["joint"]: item["rmse_px"] for item in report["per_joint"]}
    assert all(abs(value - 10.0) <= 0.01 for value in rmses.values()), rmses
    assert md.is_file() and "关键点精度报告" in md.read_text(encoding="utf-8")


@pytest.mark.skipif(not FIXTURE.is_file(), reason="缺少 golden fixture")
def test_cli_drops_unpaired_frames(tmp_path: Path):
    """candidate 少 4 帧 → dropped=4，且不产生插值帧。"""
    candidate = make_shifted_copy(FIXTURE, tmp_path / "candidate_short.xml", shift=5.0, drop_frames=4)
    out = tmp_path / "report.json"
    result = run_tool(
        "--reference", str(FIXTURE),
        "--candidate", str(candidate),
        "--format", "cvat",
        "--out", str(out),
    )
    assert result.returncode == 0, result.stderr
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["pairing"]["paired_frames"] == 100
    assert report["pairing"]["dropped"] == 4
    assert all(item["n"] == 100 for item in report["per_joint"])


def test_cli_missing_input_fails_without_output(tmp_path: Path):
    """5.11：输入不存在 → 非零退出且不产生输出文件。"""
    out = tmp_path / "should_not_exist.json"
    result = run_tool(
        "--reference", str(tmp_path / "nope.xml"),
        "--candidate", str(tmp_path / "nope.xml"),
        "--out", str(out),
    )
    assert result.returncode != 0
    assert "file_not_found" in result.stderr
    assert not out.exists()


@pytest.mark.skipif(not FIXTURE.is_file(), reason="缺少 golden fixture")
def test_cli_rejects_existing_baseline_without_force(tmp_path: Path):
    """5.12：基线已存在且无 --force → 拒绝写入，原文件不变。"""
    baseline = tmp_path / "accuracy_baseline.json"
    baseline.write_text('{"locked": true}\n', encoding="utf-8")
    before = sha256(baseline)

    result = run_tool(
        "--reference", str(FIXTURE),
        "--candidate", str(FIXTURE),
        "--format", "cvat",
        "--out", str(tmp_path / "report.json"),
        "--baseline-out", str(baseline),
    )
    assert result.returncode != 0
    assert "baseline_exists" in result.stderr
    assert sha256(baseline) == before


@pytest.mark.skipif(not FIXTURE.is_file(), reason="缺少 golden fixture")
def test_cli_force_requires_reason(tmp_path: Path):
    baseline = tmp_path / "accuracy_baseline.json"
    baseline.write_text('{"locked": true}\n', encoding="utf-8")

    result = run_tool(
        "--reference", str(FIXTURE),
        "--candidate", str(FIXTURE),
        "--format", "cvat",
        "--out", str(tmp_path / "report.json"),
        "--baseline-out", str(baseline),
        "--force",
    )
    assert result.returncode != 0
    assert "reason_required" in result.stderr


@pytest.mark.skipif(not FIXTURE.is_file(), reason="缺少 golden fixture")
def test_cli_force_with_reason_records_approval(tmp_path: Path):
    baseline = tmp_path / "accuracy_baseline.json"
    baseline.write_text('{"locked": true}\n', encoding="utf-8")

    result = run_tool(
        "--reference", str(FIXTURE),
        "--candidate", str(FIXTURE),
        "--format", "cvat",
        "--out", str(tmp_path / "report.json"),
        "--baseline-out", str(baseline),
        "--force",
        "--reason", "add-keypoint-accuracy-benchmark",
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(baseline.read_text(encoding="utf-8"))
    assert payload["approval"]["reason"] == "add-keypoint-accuracy-benchmark"
    assert payload["schema_version"] == "accuracy-report.v1"


@pytest.mark.skipif(not FIXTURE.is_file(), reason="缺少 golden fixture")
def test_cli_does_not_modify_inputs(tmp_path: Path):
    """5.13：运行前后输入文件 SHA-256 不变。"""
    candidate = make_shifted_copy(FIXTURE, tmp_path / "candidate.xml", shift=3.0)
    ref_before, cand_before = sha256(FIXTURE), sha256(candidate)

    result = run_tool(
        "--reference", str(FIXTURE),
        "--candidate", str(candidate),
        "--format", "cvat",
        "--out", str(tmp_path / "report.json"),
    )
    assert result.returncode == 0, result.stderr
    assert sha256(FIXTURE) == ref_before
    assert sha256(candidate) == cand_before


def test_cli_rejects_disjoint_frame_sets(tmp_path: Path):
    """两侧帧号空间不一致（无共同帧）→ 拒绝并给出 frame_space_mismatch。"""
    ref = tmp_path / "ref.xml"
    cand = tmp_path / "cand.xml"
    ref.write_text(_tiny_cvat([1, 2, 3]), encoding="utf-8")
    cand.write_text(_tiny_cvat([900, 901, 902]), encoding="utf-8")

    out = tmp_path / "report.json"
    result = run_tool(
        "--reference", str(ref),
        "--candidate", str(cand),
        "--format", "cvat",
        "--out", str(out),
    )
    assert result.returncode != 0
    assert "frame_space_mismatch" in result.stderr
    assert not out.exists()


def test_same_frame_numbers_different_clips_are_not_paired(tmp_path: Path):
    """多 clip 合并的真实风险：帧号相同但图像不同，绝不能按帧号配对。"""
    ref = tmp_path / "ref.xml"
    cand = tmp_path / "cand.xml"
    ref.write_text(_tiny_cvat([1, 2], prefix="clipA"), encoding="utf-8")
    cand.write_text(_tiny_cvat([1, 2], prefix="clipB"), encoding="utf-8")

    result = run_tool(
        "--reference", str(ref),
        "--candidate", str(cand),
        "--format", "cvat",
        "--out", str(tmp_path / "report.json"),
    )
    assert result.returncode != 0
    assert "frame_space_mismatch" in result.stderr


def test_cli_rejects_mixed_key_modes(tmp_path: Path):
    """一侧按图像名、另一侧按帧号 → 明确拒绝，不猜对齐方式。"""
    ref = tmp_path / "ref.xml"
    cand = tmp_path / "cand.json"
    ref.write_text(_tiny_cvat([1, 2]), encoding="utf-8")
    cand.write_text(
        json.dumps(
            {
                "keypoint_frames": [
                    {
                        "annotation_frame": 1,
                        "points": {
                            "left-shoulder": {"x": 400, "y": 300},
                            "right-shoulder": {"x": 500, "y": 300},
                            "left-ankle": {"x": 400, "y": 1200},
                            "right-ankle": {"x": 500, "y": 1200},
                        },
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    result = run_tool(
        "--reference", str(ref),
        "--candidate", str(cand),
        "--format", "auto",
        "--out", str(tmp_path / "report.json"),
    )
    assert result.returncode != 0
    assert "key_mode_mismatch" in result.stderr


def _tiny_cvat(frames: list[int], prefix: str = "frame") -> str:
    points = {
        "left-shoulder": (400.0, 300.0),
        "right-shoulder": (500.0, 300.0),
        "left-ankle": (400.0, 1200.0),
        "right-ankle": (500.0, 1200.0),
        "left-wrist": (350.0, 500.0),
        "right-wrist": (550.0, 500.0),
    }
    images = []
    for index, frame in enumerate(frames, start=1):
        nodes = "".join(
            f'<points label="{name}" outside="0" occluded="0" points="{x:.2f},{y:.2f}"></points>'
            for name, (x, y) in points.items()
        )
        images.append(
            f'<image id="{index}" name="{prefix}_f{frame:06d}.jpg" width="1920" height="1080">'
            f'<skeleton label="person">{nodes}</skeleton></image>'
        )
    return (
        '<?xml version="1.0" encoding="utf-8"?>'
        f'<annotations version="1.1">{"".join(images)}</annotations>'
    )
