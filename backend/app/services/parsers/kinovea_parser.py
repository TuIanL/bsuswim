"""Kinovea annotation parser.

Parses Kinovea-assisted JSON and fixed-column CSV annotation exports into
``ParsedKinoveaAnnotation`` — a pure-data object carrying ``swim-annotation.v1``
compatible normalized fields. The parser never touches the database.
"""
from __future__ import annotations

import csv
import json
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.normalized_annotation import (
    AnnotationEvent,
    CoordinateSystem,
    KeypointFrame,
    KeypointPoint,
    ManualTag,
    ParseSummary,
    ScaleInfo,
    Trajectory,
)


class KinoveaParseError(Exception):
    """Raised when a Kinovea annotation file cannot be parsed."""


# ── Mapping tables ──

EVENT_NAME_NORMALIZE: dict[str, str] = {
    "入水": "hand_entry",
    "抱水开始": "catch_start",
    "抱水": "catch_start",
    "推水结束": "pull_end",
    "推水": "pull_end",
    "划水周期开始": "cycle_start",
    "周期开始": "cycle_start",
    "划水周期结束": "cycle_end",
    "周期结束": "cycle_end",
}

EVENT_CODE_TO_LABEL: dict[str, str] = {
    "hand_entry": "入水",
    "catch_start": "抱水开始",
    "pull_end": "推水结束",
    "cycle_start": "划水周期开始",
    "cycle_end": "划水周期结束",
}

# 关键点别名映射（中文 / 英文常见写法 → 标准关键点名）
KEYPOINT_ALIAS_MAP: dict[str, str] = {
    "肩": "right_shoulder",
    "shoulder": "right_shoulder",
    "右肩": "right_shoulder",
    "左肩": "left_shoulder",
    "肘": "right_elbow",
    "elbow": "right_elbow",
    "右肘": "right_elbow",
    "左肘": "left_elbow",
    "腕": "right_wrist",
    "wrist": "right_wrist",
    "右腕": "right_wrist",
    "左腕": "left_wrist",
    "髋": "right_hip",
    "hip": "right_hip",
    "右髋": "right_hip",
    "左髋": "left_hip",
    "膝": "right_knee",
    "knee": "right_knee",
    "右膝": "right_knee",
    "左膝": "left_knee",
    "踝": "right_ankle",
    "ankle": "right_ankle",
    "右踝": "right_ankle",
    "左踝": "left_ankle",
}

# 标准关键点名（identity 匹配，不触发 unknown warning）
STANDARD_KEYPOINTS: set[str] = {
    "shoulder", "elbow", "wrist", "hip", "knee", "ankle",
    "right_shoulder", "right_elbow", "right_wrist", "right_hip", "right_knee", "right_ankle",
    "left_shoulder", "left_elbow", "left_wrist", "left_hip", "left_knee", "left_ankle",
}

RECOMMENDED_EVENTS = {"hand_entry", "catch_start", "pull_end", "cycle_start", "cycle_end"}

# CSV 必要列（缺一则整文件无法解析）
CSV_REQUIRED_COLUMNS = {"type", "frame", "x", "y"}

# CSV 固定 11 (+1 comment) 列
CSV_FIXED_COLUMNS = [
    "type",
    "name",
    "label",
    "frame",
    "time_sec",
    "side",
    "point",
    "x",
    "y",
    "tag",
    "severity",
    "comment",
]


class ParsedKinoveaAnnotation(BaseModel):
    """Kinovea parser 产物：纯数据，不含数据库访问。"""

    fps: float | None = None
    frame_count: int | None = None
    duration_sec: float | None = None
    scale: ScaleInfo | None = None
    coordinate_system: CoordinateSystem = Field(default_factory=CoordinateSystem)
    events: list[AnnotationEvent] = Field(default_factory=list)
    keypoint_frames: list[KeypointFrame] = Field(default_factory=list)
    trajectories: list[Trajectory] = Field(default_factory=list)
    manual_tags: list[ManualTag] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


# ── Helpers ──


def _normalize_event_name(name: str) -> str:
    name = (name or "").strip()
    return EVENT_NAME_NORMALIZE.get(name, name)


def _normalize_point_name(point: str) -> tuple[str, bool]:
    """Return ``(standard_name, matched)``. matched=False → 原样保留并提示。"""
    key = (point or "").strip().lower()
    if key in KEYPOINT_ALIAS_MAP:
        return KEYPOINT_ALIAS_MAP[key], True
    if key in STANDARD_KEYPOINTS:
        return key, True
    return (point or "").strip(), False


def _safe_int(value: Any) -> int | None:
    if value is None:
        return None
    s = str(value).strip()
    if s == "":
        return None
    try:
        return int(float(s))
    except (ValueError, TypeError):
        return None


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    s = str(value).strip()
    if s == "":
        return None
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def resolve_time_sec(row: dict[str, Any], fps: float | None) -> float:
    """解析行的 time_sec：优先用行内 time_sec，否则用 frame/fps 推导。"""
    raw_ts = (row.get("time_sec") or "").strip()
    if raw_ts:
        try:
            return float(raw_ts)
        except ValueError:
            raise KinoveaParseError(f"time_sec 不是有效数字: {raw_ts!r}")
    raw_frame = (row.get("frame") or "").strip()
    if raw_frame and fps:
        try:
            return round(int(float(raw_frame)) / fps, 3)
        except (ValueError, ZeroDivisionError):
            raise KinoveaParseError(f"无法从 frame/fps 推导 time_sec: frame={raw_frame!r}, fps={fps}")
    raise KinoveaParseError("缺少 time_sec 且无法从 frame/fps 推导（需提供 time_sec 或 fps）")


def build_semantic_warnings(events: list[AnnotationEvent]) -> list[str]:
    """推荐事件缺失时生成语义提醒，不阻止 parse 成功。"""
    present = {e.name for e in events}
    missing = RECOMMENDED_EVENTS - present
    return [f"缺少推荐事件: {name}（{EVENT_CODE_TO_LABEL.get(name, name)}）" for name in sorted(missing)]


def build_parse_summary(parsed: ParsedKinoveaAnnotation) -> ParseSummary:
    """从解析结果生成计数摘要。"""
    return ParseSummary(
        events_count=len(parsed.events),
        keypoint_frames_count=len(parsed.keypoint_frames),
        trajectories_count=len(parsed.trajectories),
        manual_tags_count=len(parsed.manual_tags),
    )


# ── JSON parsing ──


def _build_event(evt: dict[str, Any], fps: float | None = None) -> AnnotationEvent:
    name = _normalize_event_name(evt.get("name", ""))
    label = evt.get("label") or EVENT_CODE_TO_LABEL.get(name, name)
    side = (evt.get("side") or "unknown")
    if side not in ("left", "right", "both", "unknown"):
        side = "unknown"
    ts = evt.get("time_sec")
    if ts is None and evt.get("frame") is not None and fps:
        ts = round(int(evt["frame"]) / fps, 3)
    return AnnotationEvent(
        name=name,
        label=label,
        frame=int(evt.get("frame", 0) or 0),
        time_sec=float(ts) if ts is not None else 0.0,
        side=side,
        confidence=float(evt.get("confidence", 1.0)),
        labeled_by=evt.get("labeled_by") or "kinovea",
    )


def _build_keypoint_frame(kf: dict[str, Any]) -> KeypointFrame:
    points: dict[str, KeypointPoint] = {}
    raw_points = kf.get("points", {})
    if isinstance(raw_points, dict):
        for pname, pval in raw_points.items():
            std_name, _ = _normalize_point_name(pname)
            if isinstance(pval, dict):
                points[std_name] = KeypointPoint(
                    x=float(pval.get("x", 0.0)),
                    y=float(pval.get("y", 0.0)),
                    confidence=float(pval.get("confidence", 1.0)),
                    visibility=pval.get("visibility", "visible"),
                )
            else:
                points[std_name] = KeypointPoint(x=0.0, y=0.0)
    return KeypointFrame(
        frame=int(kf.get("frame", 0) or 0),
        time_sec=float(kf.get("time_sec", 0.0) or 0.0),
        phase=kf.get("phase", "") or "",
        points=points,
        tags=list(kf.get("tags", []) or []),
    )


def _build_trajectory(tr: dict[str, Any]) -> Trajectory:
    return Trajectory(
        name=tr.get("name", ""),
        label=tr.get("label") or tr.get("name") or "",
        point=tr.get("point", ""),
        frames=tr.get("frames", []) or [],
        points=tr.get("points", []) or [],
        source=tr.get("source", "kinovea"),
    )


def _build_manual_tag(tag: dict[str, Any]) -> ManualTag:
    code = (tag.get("name") or tag.get("tag") or "").strip()
    label = (tag.get("label") or "").strip() or code
    severity = (tag.get("severity") or "medium").strip().lower()
    if severity not in ("low", "medium", "high"):
        severity = "medium"
    frame = _safe_int(tag.get("frame"))
    return ManualTag(
        code=code,
        label=label,
        severity=severity,
        phase=tag.get("phase", "") or "",
        frame_range=[frame] if frame is not None else [],
        comment=tag.get("comment") or "",
    )


def parse_kinovea_json(file_path: str) -> ParsedKinoveaAnnotation:
    """解析 Kinovea-assisted JSON 标注文件。"""
    try:
        with open(file_path, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise KinoveaParseError(f"Kinovea JSON 读取/解析失败: {exc}")

    if not isinstance(raw, dict):
        raise KinoveaParseError("Kinovea JSON 根节点必须是对象")

    top_fps = raw.get("fps")
    events = [_build_event(evt, top_fps) for evt in (raw.get("events") or [])]
    keypoint_frames = [_build_keypoint_frame(kf) for kf in (raw.get("keypoint_frames") or [])]
    trajectories = [_build_trajectory(tr) for tr in (raw.get("trajectories") or [])]
    manual_tags = [_build_manual_tag(tag) for tag in (raw.get("manual_tags") or [])]

    scale = ScaleInfo(**raw["scale"]) if raw.get("scale") else None
    coordinate_system = (
        CoordinateSystem(**raw["coordinate_system"]) if raw.get("coordinate_system") else CoordinateSystem()
    )

    warnings = build_semantic_warnings(events)

    return ParsedKinoveaAnnotation(
        fps=top_fps,
        frame_count=raw.get("frame_count") or (raw.get("video") or {}).get("frame_count"),
        duration_sec=raw.get("duration_sec") or (raw.get("video") or {}).get("duration_sec"),
        scale=scale,
        coordinate_system=coordinate_system,
        events=events,
        keypoint_frames=keypoint_frames,
        trajectories=trajectories,
        manual_tags=manual_tags,
        warnings=warnings,
    )


# ── CSV parsing ──


def _build_csv_event(row: dict[str, Any], fps: float | None) -> AnnotationEvent:
    name = _normalize_event_name(row.get("name", ""))
    label = (row.get("label") or "").strip() or EVENT_CODE_TO_LABEL.get(name, name)
    side = (row.get("side") or "unknown").strip().lower()
    if side not in ("left", "right", "both", "unknown"):
        side = "unknown"
    return AnnotationEvent(
        name=name,
        label=label,
        frame=_safe_int(row.get("frame")) or 0,
        time_sec=resolve_time_sec(row, fps),
        side=side,
        confidence=1.0,
        labeled_by="kinovea",
    )


def _accumulate_keypoint(
    row: dict[str, Any],
    fps: float | None,
    keypoint_by_frame: dict[int, dict[str, Any]],
    warnings: list[str],
) -> None:
    frame = _safe_int(row.get("frame"))
    if frame is None or frame <= 0:
        raise KinoveaParseError(f"keypoint 行缺少有效 frame: {row}")
    raw_point = (row.get("point") or "").strip()
    if not raw_point:
        raise KinoveaParseError(f"keypoint 行缺少 point: {row}")
    std_name, matched = _normalize_point_name(raw_point)
    if not matched:
        warnings.append(f"未知关键点名称 '{raw_point}'，已原样保留")
    x = _safe_float(row.get("x"))
    y = _safe_float(row.get("y"))
    if x is None or y is None:
        raise KinoveaParseError(f"keypoint 坐标非数字: point={raw_point!r} x={row.get('x')!r} y={row.get('y')!r}")

    kf = keypoint_by_frame.setdefault(
        frame, {"frame": frame, "time_sec": None, "points": {}, "tags": []}
    )
    kf["points"][std_name] = KeypointPoint(x=x, y=y)

    raw_ts = (row.get("time_sec") or "").strip()
    if raw_ts:
        try:
            kf["time_sec"] = float(raw_ts)
        except ValueError:
            raise KinoveaParseError(f"time_sec 非数字: {raw_ts!r}")
    if kf["time_sec"] is None:
        if fps:
            kf["time_sec"] = round(frame / fps, 3)
        else:
            raise KinoveaParseError(
                f"keypoint 行 frame={frame} 缺少 time_sec 且未提供 fps，无法推导时间戳"
            )


def _finalize_keypoint_frames(keypoint_by_frame: dict[int, dict[str, Any]]) -> list[KeypointFrame]:
    frames = []
    for _frame, kf in sorted(keypoint_by_frame.items()):
        frames.append(
            KeypointFrame(
                frame=kf["frame"],
                time_sec=kf["time_sec"] if kf["time_sec"] is not None else 0.0,
                phase="",
                points=kf["points"],
                tags=kf["tags"],
            )
        )
    return frames


def _build_csv_trajectories(trajectory_rows: list[dict[str, Any]]) -> list[Trajectory]:
    by_name: dict[str, dict[str, Any]] = {}
    for row in trajectory_rows:
        name = (row.get("name") or "").strip()
        if not name:
            continue
        tr = by_name.setdefault(
            name,
            {
                "name": name,
                "label": (row.get("label") or "").strip(),
                "point": (row.get("point") or "").strip(),
                "frames": [],
                "points": [],
                "source": "kinovea",
            },
        )
        frame = _safe_int(row.get("frame"))
        x = _safe_float(row.get("x"))
        y = _safe_float(row.get("y"))
        if frame is None or x is None or y is None:
            raise KinoveaParseError(f"trajectory 行数据不完整: {row}")
        tr["frames"].append(frame)
        tr["points"].append([x, y])
    return [
        Trajectory(
            name=tr["name"],
            label=tr["label"] or tr["name"],
            point=tr["point"],
            frames=tr["frames"],
            points=tr["points"],
            source=tr["source"],
        )
        for tr in by_name.values()
    ]


def parse_kinovea_csv(file_path: str, fallback_fps: float | None = None) -> ParsedKinoveaAnnotation:
    """解析固定列名 Kinovea CSV 标注文件。"""
    try:
        with open(file_path, "r", encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            header = reader.fieldnames or []
            missing_cols = CSV_REQUIRED_COLUMNS - set(header)
            if missing_cols:
                raise KinoveaParseError(f"CSV 缺少必要列: {', '.join(sorted(missing_cols))}")
            rows = list(reader)
    except (FileNotFoundError, OSError) as exc:
        raise KinoveaParseError(f"Kinovea CSV 读取失败: {exc}")

    events: list[AnnotationEvent] = []
    keypoint_by_frame: dict[int, dict[str, Any]] = {}
    trajectory_rows: list[dict[str, Any]] = []
    tags: list[ManualTag] = []
    warnings: list[str] = []

    for row in rows:
        rtype = (row.get("type") or "").strip().lower()
        if not rtype:
            continue
        if rtype == "event":
            events.append(_build_csv_event(row, fallback_fps))
        elif rtype == "keypoint":
            _accumulate_keypoint(row, fallback_fps, keypoint_by_frame, warnings)
        elif rtype == "trajectory":
            trajectory_rows.append(row)
        elif rtype == "tag":
            tags.append(_build_manual_tag(row))
        # 未知 type 静默跳过（MVP 不支持）

    keypoint_frames = _finalize_keypoint_frames(keypoint_by_frame)
    trajectories = _build_csv_trajectories(trajectory_rows)

    warnings.extend(build_semantic_warnings(events))

    return ParsedKinoveaAnnotation(
        fps=fallback_fps,
        scale=None,
        events=events,
        keypoint_frames=keypoint_frames,
        trajectories=trajectories,
        manual_tags=tags,
        warnings=warnings,
    )


# ── Dispatcher ──


def parse_kinovea_annotation(
    file_path: str, file_type: str, fallback_fps: float | None = None
) -> ParsedKinoveaAnnotation:
    """根据 file_type 选择 JSON / CSV parser（MVP 不嗅探内容）。"""
    file_type = (file_type or "").strip().lower()
    if file_type == "json":
        return parse_kinovea_json(file_path)
    if file_type == "csv":
        return parse_kinovea_csv(file_path, fallback_fps=fallback_fps)
    raise KinoveaParseError(f"不支持的 file_type: {file_type!r}（Kinovea parser 仅支持 json / csv）")
