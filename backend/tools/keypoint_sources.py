"""三种关键点输入的读取、关节名规范化与参考尺度计算。

支持格式：
- ``cvat``       CVAT 1.1 image-based skeleton XML
- ``coco``       COCO keypoints JSON（``images`` + ``annotations`` + ``categories``）
- ``normalized`` 归一化后的 ``keypoint_frames`` JSON

统一内存结构：``{frame_number: {joint_name: Point}}``，关节名一律规范化为
连字符小写形式（``left-shoulder``）。

本模块只用标准库，不 import ``app.*``。
"""

from __future__ import annotations

import hashlib
import json
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from statistics import median

COCO17_JOINTS: tuple[str, ...] = (
    "nose",
    "left-eye",
    "right-eye",
    "left-ear",
    "right-ear",
    "left-shoulder",
    "right-shoulder",
    "left-elbow",
    "right-elbow",
    "left-wrist",
    "right-wrist",
    "left-hip",
    "right-hip",
    "left-knee",
    "right-knee",
    "left-ankle",
    "right-ankle",
)

_FRAME_DIGITS = re.compile(r"(\d+)(?=\D*$)")


class KeypointSourceError(Exception):
    """输入不可解析或不符合契约。"""

    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


@dataclass(frozen=True)
class Point:
    x: float
    y: float
    visible: bool = True
    occluded: bool = False


@dataclass
class KeypointSet:
    """统一关键点集合。

    ``frames`` 的键是**配对键**：优先使用图像基名（stem），无法取得时回退为
    帧号字符串。多 clip 合并且在帧号重叠时，只有基名能唯一定位一帧。
    """

    frames: dict[str, dict[str, Point]]
    source_format: str
    path: Path
    sha256: str
    key_mode: str = "image_name"
    skipped_points: int = 0

    @property
    def frame_keys(self) -> list[str]:
        return sorted(self.frames)

    @property
    def joints(self) -> list[str]:
        found: set[str] = set()
        for points in self.frames.values():
            found.update(points)
        known = [j for j in COCO17_JOINTS if j in found]
        extra = sorted(found - set(known))
        return known + extra


def normalize_joint_name(name: str) -> str:
    """小写 + 下划线/空格统一为连字符（``left_shoulder`` → ``left-shoulder``）。"""
    return re.sub(r"[\s_]+", "-", str(name).strip().lower())


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _frame_from_name(name: str) -> int | None:
    match = _FRAME_DIGITS.search(Path(name).stem)
    return int(match.group(1)) if match else None


def _parse_xy(raw: str) -> tuple[float, float] | None:
    parts = [p for p in raw.replace(";", ",").split(",") if p.strip()]
    if len(parts) < 2:
        return None
    try:
        return float(parts[0]), float(parts[1])
    except ValueError:
        return None


def read_cvat_xml(path: Path) -> KeypointSet:
    """读取 CVAT 1.1 image-based skeleton XML。

    - ``outside="1"`` → ``visible=False``
    - ``occluded="1"`` → 仍视为已标注（``visible=True``），另记 ``occluded=True``
    - 帧号取文件名末尾数字（如 ``frame_00000270.jpg`` → 270）；取不到时回退为顺序索引
    """
    try:
        root = ET.parse(str(path)).getroot()
    except (ET.ParseError, OSError) as exc:
        raise KeypointSourceError("cvat_parse_failed", f"{path}: {exc}") from exc

    frames: dict[str, dict[str, Point]] = {}
    skipped = 0
    for image in root.findall(".//image"):
        name = image.get("name") or ""
        stem = Path(name).stem
        if not stem:
            raise KeypointSourceError(
                "cvat_missing_image_name",
                f"{path}: image id={image.get('id')} 缺少 name，无法建立可靠配对键",
            )
        key = stem

        points: dict[str, Point] = {}
        for skeleton in image.findall(".//skeleton"):
            for node in skeleton.findall("points"):
                label = node.get("label")
                if not label:
                    continue
                joint = normalize_joint_name(label)
                outside = node.get("outside") == "1"
                occluded = node.get("occluded") == "1"
                xy = _parse_xy(node.get("points") or "")
                if outside or xy is None:
                    skipped += 1
                    continue
                points[joint] = Point(x=xy[0], y=xy[1], visible=True, occluded=occluded)
        if points:
            frames[key] = points

    if not frames:
        raise KeypointSourceError("cvat_no_frames", f"{path}: 未解析到任何带骨架的帧")
    return KeypointSet(
        frames=frames,
        source_format="cvat",
        path=path,
        sha256=sha256_file(path),
        key_mode="image_name",
        skipped_points=skipped,
    )


def read_coco_json(path: Path) -> KeypointSet:
    """读取 COCO keypoints JSON。

    ``keypoints`` 为扁平 ``[x, y, v] * n``；``v == 0`` 视为未标注，不计入。
    """
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise KeypointSourceError("coco_parse_failed", f"{path}: {exc}") from exc

    if not isinstance(payload, dict) or "annotations" not in payload:
        raise KeypointSourceError("coco_missing_annotations", f"{path}: 缺少 annotations")

    categories = payload.get("categories") or []
    names = list(COCO17_JOINTS)
    if categories and isinstance(categories[0], dict):
        declared = categories[0].get("keypoints")
        if isinstance(declared, list) and declared:
            names = [normalize_joint_name(n) for n in declared]

    image_list = [img for img in payload.get("images") or [] if isinstance(img, dict)]
    images = {img.get("id"): img for img in image_list}
    use_name = bool(image_list) and all(str(img.get("file_name") or "").strip() for img in image_list)
    key_mode = "image_name" if use_name else "image_id"

    frames: dict[str, dict[str, Point]] = {}
    skipped = 0
    for ann in payload.get("annotations") or []:
        if not isinstance(ann, dict):
            continue
        image = images.get(ann.get("image_id")) or {}
        if use_name:
            key = Path(str(image.get("file_name"))).stem
        else:
            key = str(image.get("id", ann.get("image_id")))

        flat = ann.get("keypoints") or []
        if not isinstance(flat, list) or len(flat) < 3:
            skipped += 1
            continue

        points: dict[str, Point] = {}
        for idx in range(len(flat) // 3):
            if idx >= len(names):
                skipped += 1
                break
            x, y, v = flat[idx * 3 : idx * 3 + 3]
            if v is None or float(v) <= 0:
                skipped += 1
                continue
            points[names[idx]] = Point(x=float(x), y=float(y), visible=True)
        if points:
            frames[key] = points

    if not frames:
        raise KeypointSourceError("coco_no_frames", f"{path}: 未解析到任何可用帧")
    return KeypointSet(
        frames=frames,
        source_format="coco",
        path=path,
        sha256=sha256_file(path),
        key_mode=key_mode,
        skipped_points=skipped,
    )


def read_normalized_json(path: Path) -> KeypointSet:
    """读取归一化 ``keypoint_frames`` JSON（``points`` 支持 dict 或 list 两种写法）。"""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise KeypointSourceError("normalized_parse_failed", f"{path}: {exc}") from exc

    if isinstance(payload, dict):
        raw_frames = payload.get("keypoint_frames") or payload.get("frames") or []
    elif isinstance(payload, list):
        raw_frames = payload
    else:
        raise KeypointSourceError("normalized_invalid", f"{path}: 顶层结构不是对象或数组")

    frames: dict[str, dict[str, Point]] = {}
    skipped = 0
    key_mode = "frame_number"
    for index, item in enumerate(raw_frames):
        if not isinstance(item, dict):
            continue
        if item.get("frame_key") is not None:
            key = str(item["frame_key"])
            key_mode = "frame_key"
        else:
            frame = item.get("annotation_frame")
            if frame is None:
                frame = item.get("frame", index)
            key = str(int(frame))

        raw_points = item.get("points") or {}
        points: dict[str, Point] = {}
        if isinstance(raw_points, dict):
            iterable = raw_points.items()
            for name, value in iterable:
                if not isinstance(value, dict):
                    skipped += 1
                    continue
                joint = normalize_joint_name(name)
                visibility = str(value.get("visibility", "visible"))
                if visibility == "missing":
                    skipped += 1
                    continue
                x, y = value.get("x"), value.get("y")
                if x is None or y is None:
                    skipped += 1
                    continue
                points[joint] = Point(
                    x=float(x), y=float(y), visible=True, occluded=visibility == "occluded"
                )
        else:
            for value in raw_points:
                if not isinstance(value, dict):
                    skipped += 1
                    continue
                label = value.get("name") or value.get("label")
                if not label:
                    skipped += 1
                    continue
                joint = normalize_joint_name(label)
                if value.get("visible") is False or value.get("visibility") == "missing":
                    skipped += 1
                    continue
                x, y = value.get("x"), value.get("y")
                if x is None or y is None:
                    skipped += 1
                    continue
                points[joint] = Point(x=float(x), y=float(y), visible=True)
        if points:
            frames[key] = points

    if not frames:
        raise KeypointSourceError("normalized_no_frames", f"{path}: 未解析到任何可用帧")
    return KeypointSet(
        frames=frames,
        source_format="normalized",
        path=path,
        sha256=sha256_file(path),
        key_mode=key_mode,
        skipped_points=skipped,
    )


def detect_format(path: Path) -> str:
    if path.suffix.lower() == ".xml":
        return "cvat"
    if path.suffix.lower() in {".json", ".jsonl"}:
        head = path.read_text(encoding="utf-8")[:4096]
        if '"annotations"' in head and '"images"' in head:
            return "coco"
        return "normalized"
    raise KeypointSourceError("unknown_format", f"{path}: 仅支持 .xml 与 .json")


def read_keypoints(path: str | Path, fmt: str = "auto") -> KeypointSet:
    p = Path(path)
    if not p.is_file():
        raise KeypointSourceError("file_not_found", str(p))
    resolved = detect_format(p) if fmt in {"auto", None} else fmt
    readers = {
        "cvat": read_cvat_xml,
        "coco": read_coco_json,
        "normalized": read_normalized_json,
    }
    if resolved not in readers:
        raise KeypointSourceError("unknown_format", f"不支持的格式: {resolved}")
    return readers[resolved](p)


def align_joints(
    reference: KeypointSet, candidate: KeypointSet
) -> tuple[list[str], list[dict[str, str]]]:
    """返回（双方共有关节, 被跳过的关节及原因）。不猜测、不补点。"""
    ref_joints = set(reference.joints)
    cand_joints = set(candidate.joints)
    common = [j for j in COCO17_JOINTS if j in ref_joints and j in cand_joints]
    common += sorted((ref_joints & cand_joints) - set(COCO17_JOINTS))

    skipped: list[dict[str, str]] = []
    for joint in sorted(ref_joints - cand_joints):
        skipped.append({"joint": joint, "reason": "missing_in_candidate"})
    for joint in sorted(cand_joints - ref_joints):
        skipped.append({"joint": joint, "reason": "missing_in_reference"})
    return common, skipped


def reference_body_length(frames: dict[str, dict[str, Point]]) -> float | None:
    """肩中点→踝中点距离的中位数（与生产 ``compute_reference_body_length`` 同口径）。

    只使用四点（双肩、双踝）均可见的帧。
    """
    required = ("left-shoulder", "right-shoulder", "left-ankle", "right-ankle")
    distances: list[float] = []
    for points in frames.values():
        if not all(j in points and points[j].visible for j in required):
            continue
        ls, rs = points["left-shoulder"], points["right-shoulder"]
        la, ra = points["left-ankle"], points["right-ankle"]
        sx, sy = (ls.x + rs.x) / 2.0, (ls.y + rs.y) / 2.0
        ax, ay = (la.x + ra.x) / 2.0, (la.y + ra.y) / 2.0
        dist = ((sx - ax) ** 2 + (sy - ay) ** 2) ** 0.5
        if dist > 0:
            distances.append(dist)
    if not distances:
        return None
    return round(median(distances), 2)
