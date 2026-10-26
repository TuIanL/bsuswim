#!/usr/bin/env python3
"""关键点精度评估 CLI（只读、离屏、无数据库依赖）。

用法示例：

    python tools/eval_keypoints.py \
        --reference tests/fixtures/kinematics_golden_v1/source/annotations.xml \
        --candidate second_annotator.xml \
        --out /tmp/accuracy_report.json \
        --md-out /tmp/accuracy_report.md

设计说明见 openspec/changes/add-keypoint-accuracy-benchmark/design.md。
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

# 允许直接 `python tools/eval_keypoints.py`（此时 sys.path[0] 是 tools/ 而非 backend/）
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.keypoint_metrics import (  # noqa: E402
    COCO17_SIGMAS,
    PCK_THRESHOLDS,
    SIGMA_TABLE_ID,
    rank_and_aggregate,
    resolve_area,
    score_joint,
)
from tools.keypoint_sources import (  # noqa: E402
    KeypointSourceError,
    align_joints,
    read_keypoints,
    reference_body_length,
)

SCHEMA_VERSION = "accuracy-report.v1"
ICC_CAVEAT = "ICC 受相邻帧自相关影响，仅作一致性参考，不作为显著性结论"


class EvalError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="eval_keypoints",
        description="比较两份关键点标注的逐关节精度（只读工具）",
    )
    parser.add_argument("--reference", required=True, help="基准关键点（人工标注）")
    parser.add_argument("--candidate", required=True, help="待评估关键点（第二标注或模型输出）")
    parser.add_argument(
        "--format",
        default="auto",
        choices=["auto", "cvat", "coco", "normalized"],
        help="输入格式；auto 按扩展名与内容嗅探",
    )
    parser.add_argument("--out", required=True, help="accuracy-report JSON 输出路径")
    parser.add_argument("--md-out", help="可选：人可读 markdown 表输出路径")
    parser.add_argument("--baseline-out", help="可选：固化为 accuracy_baseline.json")
    parser.add_argument("--force", action="store_true", help="允许覆盖已存在的基线文件")
    parser.add_argument("--reason", help="覆盖基线时必须提供的理由（change-id 等）")
    parser.add_argument(
        "--frame-space",
        default="annotation",
        choices=["annotation", "source"],
        help="两份输入使用的帧号空间；两侧必须一致",
    )
    return parser


def _assert_finite(obj, path: str = "$") -> None:
    if isinstance(obj, float):
        if not math.isfinite(obj):
            raise EvalError("non_finite_value", f"{path} 不是有限数值: {obj}")
        return
    if isinstance(obj, dict):
        for key, value in obj.items():
            _assert_finite(value, f"{path}.{key}")
        return
    if isinstance(obj, list):
        for index, value in enumerate(obj):
            _assert_finite(value, f"{path}[{index}]")


def evaluate(reference_path: str, candidate_path: str, fmt: str, frame_space: str) -> dict:
    try:
        reference = read_keypoints(reference_path, fmt)
        candidate = read_keypoints(candidate_path, fmt)
    except KeypointSourceError as exc:
        raise EvalError(exc.code, exc.message) from exc

    if reference.key_mode != candidate.key_mode:
        raise EvalError(
            "key_mode_mismatch",
            f"配对键模式不一致：reference={reference.key_mode}，"
            f"candidate={candidate.key_mode}；请把两侧导出为同一种格式",
        )

    paired = sorted(set(reference.frames) & set(candidate.frames))
    if not paired:
        raise EvalError(
            "frame_space_mismatch",
            f"两份输入没有任何共同帧（reference {len(reference.frames)} 帧，"
            f"candidate {len(candidate.frames)} 帧；配对键模式 "
            f"reference={reference.key_mode} / candidate={candidate.key_mode}）；"
            f"多 clip 合并时请确认两份文件来自同一批图像",
        )

    body_length = reference_body_length(reference.frames)
    if body_length is None:
        raise EvalError(
            "reference_scale_unavailable",
            "无法从 reference 计算参考体长（需要双肩与双踝同时可见的帧）",
        )

    area, area_source = resolve_area(reference.frames, body_length)
    common, skipped = align_joints(reference, candidate)

    scores = []
    for joint in common:
        score = score_joint(reference.frames, candidate.frames, joint, body_length, area)
        if score is None:
            skipped.append({"joint": joint, "reason": "no_paired_samples"})
            continue
        scores.append(score)

    if not scores:
        raise EvalError("no_evaluable_joints", "没有任何关节具备可评估的配对样本")

    per_joint, aggregate = rank_and_aggregate(scores)

    caveats = [ICC_CAVEAT]
    if area_source == "body_length_fallback":
        caveats.append("OKS 目标面积回退为 (0.5×参考体长)²：参考包围盒退化，OKS 仅作相对参考")
    else:
        caveats.append("OKS 目标面积取参考关键点包围盒，会随姿态变化；跨视频比较需谨慎")
    if len(paired) < len(reference.frames):
        caveats.append(
            f"仅 {len(paired)}/{len(reference.frames)} 帧参与评估，未配对帧不参与任何指标计算"
        )

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "inputs": {
            "reference": {
                "path": str(Path(reference_path)),
                "sha256": reference.sha256,
                "frames": len(reference.frames),
                "format": reference.source_format,
            },
            "candidate": {
                "path": str(Path(candidate_path)),
                "sha256": candidate.sha256,
                "frames": len(candidate.frames),
                "format": candidate.source_format,
            },
        },
        "pairing": {
            "frame_space": frame_space,
            "key_mode": reference.key_mode,
            "paired_frames": len(paired),
            "dropped": len(reference.frames) - len(paired),
            "overlap_ratio": round(len(paired) / len(reference.frames), 4),
        },
        "params": {
            "reference_body_length_px": body_length,
            "pck_thresholds": list(PCK_THRESHOLDS),
            "oks_sigmas": SIGMA_TABLE_ID,
            "oks_sigma_count": len(COCO17_SIGMAS),
            "area_px": round(area, 2),
            "area_source": area_source,
        },
        "per_joint": per_joint,
        "aggregate": aggregate,
        "skipped_joints": skipped,
        "caveats": caveats,
    }


def _write_json(path: Path, payload: dict) -> None:
    _assert_finite(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _render_markdown(report: dict) -> str:
    header = (
        f"# 关键点精度报告\n\n"
        f"- 生成时间：{report['generated_at']}\n"
        f"- 参考体长：{report['params']['reference_body_length_px']} px\n"
        f"- 配对帧：{report['pairing']['paired_frames']}"
        f"（丢弃 {report['pairing']['dropped']}，帧号空间 {report['pairing']['frame_space']}）\n"
        f"- 评估关节：{report['aggregate']['joints_evaluated']}\n\n"
    )
    table = (
        "| 排名 | 关节 | n | RMSE(px) | RMSE/体长 | PCK@0.02 | PCK@0.05 | PCK@0.10 | OKS | ICC |\n"
        "|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|\n"
    )
    for item in report["per_joint"]:
        icc = item["icc"]
        table += (
            f"| {item['rank']} | {item['joint']} | {item['n']} | {item['rmse_px']:.2f} | "
            f"{item['rmse_norm']:.4f} | {item['pck']['0.02']:.2f} | {item['pck']['0.05']:.2f} | "
            f"{item['pck']['0.10']:.2f} | {item['oks']:.3f} | "
            f"{'—' if icc is None else f'{icc:.3f}'} |\n"
        )
    worst = "、".join(report["aggregate"]["worst_three"]) or "—"
    tail = f"\n最差三关节：{worst}\n"
    if report["skipped_joints"]:
        skipped = "；".join(f"{s['joint']}({s['reason']})" for s in report["skipped_joints"])
        tail += f"\n跳过关节：{skipped}\n"
    tail += "\n限制：\n" + "".join(f"- {c}\n" for c in report["caveats"])
    return header + table + tail


def _write_baseline(payload: dict, path: Path, force: bool, reason: str | None) -> None:
    if path.exists():
        if not force:
            raise EvalError(
                "baseline_exists",
                f"{path} 已存在；更新基线需同时提供 --force 与 --reason",
            )
        if not reason:
            raise EvalError("reason_required", "--force 必须同时提供 --reason")
        payload = dict(payload)
        payload["approval"] = {
            "reason": reason,
            "at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
    else:
        payload = dict(payload)
        payload["approval"] = None
    _write_json(path, payload)


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        report = evaluate(args.reference, args.candidate, args.format, args.frame_space)
        out_path = Path(args.out)
        _write_json(out_path, report)
        if args.md_out:
            md_path = Path(args.md_out)
            md_path.parent.mkdir(parents=True, exist_ok=True)
            md_path.write_text(_render_markdown(report), encoding="utf-8")
        if args.baseline_out:
            _write_baseline(report, Path(args.baseline_out), args.force, args.reason)
    except EvalError as exc:
        print(f"[eval_keypoints] {exc.code}: {exc.message}", file=sys.stderr)
        return 1

    print(
        f"[eval_keypoints] 完成：{report['pairing']['paired_frames']} 帧、"
        f"{report['aggregate']['joints_evaluated']} 关节 → {args.out}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
