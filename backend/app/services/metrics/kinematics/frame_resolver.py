"""COCO17 左右分侧骨架适配层：把逐帧 keypoint_frames 解析为
``CanonicalKinematicFrame``，并合成 shoulder_mid / hip_mid / ankle_mid /
trunk_mid / head_center 等中点，逐个追踪 ``construction_mode``。

设计要点（对应 design D6 / tasks 3.x）：
- 每个合成点独立追踪 construction_mode（bilateral_midpoint / left_proxy /
  right_proxy / unavailable）。
- 单侧可用时回退为代理点，置信度 ×0.5，并标记 SINGLE_SIDE_FALLBACK。
- 保留 annotation_frame / source_video_frame 来源。
- 跨帧时序指标按 mode_signature 分组（见各 metric 模块），禁止拼接不同 mode。
"""

from dataclasses import dataclass
from enum import StrEnum
from statistics import median
from typing import Any

from app.schemas.metrics import ReferenceBodyLength


class ConstructionMode(StrEnum):
    BILATERAL_MIDPOINT = "bilateral_midpoint"
    LEFT_PROXY = "left_proxy"
    RIGHT_PROXY = "right_proxy"
    UNAVAILABLE = "unavailable"


# ── COCO17 17 关键点 ──

COCO17_KEYPOINTS: tuple[str, ...] = (
    "nose", "left_eye", "right_eye", "left_ear", "right_ear",
    "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
    "left_wrist", "right_wrist", "left_hip", "right_hip",
    "left_knee", "right_knee", "left_ankle", "right_ankle",
)

LEFT_SIDE: tuple[str, ...] = (
    "left_shoulder", "left_elbow", "left_wrist",
    "left_hip", "left_knee", "left_ankle",
)
RIGHT_SIDE: tuple[str, ...] = (
    "right_shoulder", "right_elbow", "right_wrist",
    "right_hip", "right_knee", "right_ankle",
)

_VIS_WEIGHT = {
    "visible": 1.0,
    "occluded": 0.7,
    "estimated": 0.5,
    "missing": 0.0,
}


@dataclass
class PointSample:
    """单个原始关键点采样，携带可见性派生的置信度。"""

    name: str
    x: float | None
    y: float | None
    visibility: str
    confidence: float
    available: bool


@dataclass
class ConstructedPoint:
    """合成的派生点或中点，携带 construction_mode 与置信度。"""

    x: float | None
    y: float | None
    mode: ConstructionMode
    confidence: float
    available: bool


@dataclass
class CanonicalKinematicFrame:
    """一帧解析后的规范运动学骨架。"""

    frame_index: int
    annotation_frame: int | None
    source_video_frame: int | None
    time_sec: float

    points: dict[str, PointSample]
    shoulder_mid: ConstructedPoint
    hip_mid: ConstructedPoint
    ankle_mid: ConstructedPoint
    trunk_mid: ConstructedPoint
    head_center: ConstructedPoint

    @property
    def usable(self) -> bool:
        """是否有可用的肩/髋/踝中点以支撑任一指标。"""
        return (
            self.shoulder_mid.available
            or self.hip_mid.available
            or self.ankle_mid.available
        )


def _vis_weight(visibility: str) -> float:
    return _VIS_WEIGHT.get(visibility, 0.0)


def _to_sample(name: str, raw: Any) -> PointSample:
    if not isinstance(raw, dict):
        return PointSample(name, None, None, "missing", 0.0, False)
    vis = raw.get("visibility", "visible")
    if vis == "missing":
        return PointSample(name, None, None, "missing", 0.0, False)
    x = raw.get("x")
    y = raw.get("y")
    if x is None or y is None:
        return PointSample(name, None, None, vis or "missing", 0.0, False)
    return PointSample(name, float(x), float(y), vis, _vis_weight(vis), True)


def _geom_mean(a: float, b: float) -> float:
    if a <= 0 or b <= 0:
        return 0.0
    return (a * b) ** 0.5


def _derived_mode(modes: list[ConstructionMode]) -> ConstructionMode:
    """由两个输入点的 mode 推导合成点 mode。

    - 全部 bilateral → bilateral
    - 全部同一 proxy → 该 proxy
    - 混合（bilateral+proxy 或 left+right）→ unavailable（禁止拼接）
    """
    modes = [m for m in modes if m != ConstructionMode.UNAVAILABLE]
    if not modes:
        return ConstructionMode.UNAVAILABLE
    if all(m == ConstructionMode.BILATERAL_MIDPOINT for m in modes):
        return ConstructionMode.BILATERAL_MIDPOINT
    non_bi = [m for m in modes if m != ConstructionMode.BILATERAL_MIDPOINT]
    if len(non_bi) == len(modes) and all(m == non_bi[0] for m in non_bi):
        return non_bi[0]
    return ConstructionMode.UNAVAILABLE


def _build_bilateral(
    left: PointSample | None,
    right: PointSample | None,
    single_proxy_mode: ConstructionMode | None = None,
) -> ConstructedPoint:
    """构建肩/髋/踝中点。

    - 双侧可用 → midpoint，bilateral_midpoint，置信度 = geom_mean
    - 仅单侧可用 → 代理该侧，置信度 = vis_weight × 0.5
    - 都不可用 → unavailable
    """
    l_ok = left is not None and left.available
    r_ok = right is not None and right.available
    if l_ok and r_ok:
        assert left is not None and right is not None
        x = (left.x + right.x) / 2.0
        y = (left.y + right.y) / 2.0
        conf = _geom_mean(left.confidence, right.confidence)
        return ConstructedPoint(x, y, ConstructionMode.BILATERAL_MIDPOINT, conf, True)
    if l_ok and not r_ok:
        assert left is not None
        return ConstructedPoint(
            left.x, left.y, ConstructionMode.LEFT_PROXY, left.confidence * 0.5, True
        )
    if r_ok and not l_ok:
        assert right is not None
        return ConstructedPoint(
            right.x, right.y, ConstructionMode.RIGHT_PROXY, right.confidence * 0.5, True
        )
    return ConstructedPoint(None, None, ConstructionMode.UNAVAILABLE, 0.0, False)


def _build_head_center(left_eye, right_eye, nose) -> ConstructedPoint:
    le = left_eye if (left_eye and left_eye.available) else None
    re = right_eye if (right_eye and right_eye.available) else None
    ns = nose if (nose and nose.available) else None
    if le and re:
        x = (le.x + re.x) / 2.0
        y = (le.y + re.y) / 2.0
        conf = _geom_mean(le.confidence, re.confidence)
        return ConstructedPoint(x, y, ConstructionMode.BILATERAL_MIDPOINT, conf, True)
    if le and not re:
        return ConstructedPoint(le.x, le.y, ConstructionMode.LEFT_PROXY, le.confidence * 0.5, True)
    if re and not le:
        return ConstructedPoint(re.x, re.y, ConstructionMode.RIGHT_PROXY, re.confidence * 0.5, True)
    if ns:
        # 仅鼻子可用：单一代理点
        return ConstructedPoint(ns.x, ns.y, ConstructionMode.LEFT_PROXY, ns.confidence * 0.5, True)
    return ConstructedPoint(None, None, ConstructionMode.UNAVAILABLE, 0.0, False)


def _build_trunk(shoulder_mid: ConstructedPoint, hip_mid: ConstructedPoint) -> ConstructedPoint:
    """躯干中点 = shoulder_mid 与 hip_mid 的中点，mode 由二者推导。"""
    if shoulder_mid.available and hip_mid.available:
        x = (shoulder_mid.x + hip_mid.x) / 2.0
        y = (shoulder_mid.y + hip_mid.y) / 2.0
        mode = _derived_mode([shoulder_mid.mode, hip_mid.mode])
        conf = _geom_mean(shoulder_mid.confidence, hip_mid.confidence)
        return ConstructedPoint(x, y, mode, conf, mode != ConstructionMode.UNAVAILABLE)
    if shoulder_mid.available and not hip_mid.available:
        return ConstructedPoint(
            shoulder_mid.x, shoulder_mid.y, shoulder_mid.mode, shoulder_mid.confidence * 0.5, True
        )
    if hip_mid.available and not shoulder_mid.available:
        return ConstructedPoint(
            hip_mid.x, hip_mid.y, hip_mid.mode, hip_mid.confidence * 0.5, True
        )
    return ConstructedPoint(None, None, ConstructionMode.UNAVAILABLE, 0.0, False)


def resolve_frames(keypoint_frames: list[dict]) -> list[CanonicalKinematicFrame]:
    """把 annotation 的 keypoint_frames 解析为规范骨架帧列表。"""
    out: list[CanonicalKinematicFrame] = []
    for idx, kf in enumerate(keypoint_frames):
        if not isinstance(kf, dict):
            continue
        pts_raw = kf.get("points", {}) or {}
        points = {name: _to_sample(name, pts_raw.get(name)) for name in COCO17_KEYPOINTS}

        shoulder_mid = _build_bilateral(points.get("left_shoulder"), points.get("right_shoulder"))
        hip_mid = _build_bilateral(points.get("left_hip"), points.get("right_hip"))
        ankle_mid = _build_bilateral(points.get("left_ankle"), points.get("right_ankle"))
        trunk_mid = _build_trunk(shoulder_mid, hip_mid)
        head_center = _build_head_center(
            points.get("left_eye"), points.get("right_eye"), points.get("nose")
        )

        out.append(
            CanonicalKinematicFrame(
                frame_index=idx,
                annotation_frame=kf.get("annotation_frame"),
                source_video_frame=kf.get("source_video_frame"),
                time_sec=float(kf.get("time_sec", idx)),
                points=points,
                shoulder_mid=shoulder_mid,
                hip_mid=hip_mid,
                ankle_mid=ankle_mid,
                trunk_mid=trunk_mid,
                head_center=head_center,
            )
        )
    return out


def compute_reference_body_length(frames: list[CanonicalKinematicFrame]) -> ReferenceBodyLength:
    """逐帧计算 shoulder_mid→ankle_mid 距离的中位数作为参考体长（像素）。

    仅用两侧中点都可用（bilateral）的帧，避免单侧代理污染尺度。
    """
    dists: list[float] = []
    source_frames: list[int] = []
    confs: list[float] = []
    for f in frames:
        if (
            f.shoulder_mid.available
            and f.ankle_mid.available
            and f.shoulder_mid.mode == ConstructionMode.BILATERAL_MIDPOINT
            and f.ankle_mid.mode == ConstructionMode.BILATERAL_MIDPOINT
        ):
            ax, ay = f.shoulder_mid.x, f.shoulder_mid.y
            bx, by = f.ankle_mid.x, f.ankle_mid.y
            dist = ((ax - bx) ** 2 + (ay - by) ** 2) ** 0.5
            if dist > 0:
                dists.append(dist)
                confs.append(min(f.shoulder_mid.confidence, f.ankle_mid.confidence))
                fidx = f.annotation_frame if f.annotation_frame is not None else f.frame_index
                source_frames.append(fidx)

    sample_count = len(dists)
    if sample_count == 0:
        return ReferenceBodyLength(
            value_px=None, sample_count=0, availability="unavailable", confidence=0.0,
            source_frames=[],
        )
    value_px = round(median(dists), 2)
    med_conf = round(median(confs), 3)
    if sample_count >= 8:
        availability = "available"
    elif sample_count >= 3:
        availability = "low_confidence"
    else:
        availability = "unavailable"
    return ReferenceBodyLength(
        value_px=value_px,
        sample_count=sample_count,
        availability=availability,
        confidence=med_conf,
        source_frames=source_frames,
    )
