"""关键点精度指标：纯函数，无 I/O。

口径约定（见 design.md Decision 1–5）：
- 距离一律欧氏像素距离；
- ``*_norm`` 以参考体长（肩中点→踝中点距离中位数）为分母；
- PCK 阈值以参考体长为单位；
- OKS 用 COCO17 sigmas，面积取参考关键点包围盒（退化时回退 ``(0.5×体长)²``）；
- ICC 以帧为 subject、标注员为 rater，x/y 分别计算后取较小值。
"""

from __future__ import annotations

from dataclasses import dataclass
from math import exp, sqrt

from .keypoint_sources import Point

PCK_THRESHOLDS: tuple[float, ...] = (0.02, 0.05, 0.10)

# COCO 官方 17 关节 sigma（person_keypoints_val2017 口径）
COCO17_SIGMAS: dict[str, float] = {
    "nose": 0.026,
    "left-eye": 0.025,
    "right-eye": 0.025,
    "left-ear": 0.035,
    "right-ear": 0.035,
    "left-shoulder": 0.079,
    "right-shoulder": 0.079,
    "left-elbow": 0.072,
    "right-elbow": 0.072,
    "left-wrist": 0.062,
    "right-wrist": 0.062,
    "left-hip": 0.107,
    "right-hip": 0.107,
    "left-knee": 0.087,
    "right-knee": 0.087,
    "left-ankle": 0.089,
    "right-ankle": 0.089,
}
SIGMA_TABLE_ID = "coco17.v1"

_AREA_MIN_RATIO = 0.05  # 包围盒面积低于 (0.05×体长)² 视为退化


@dataclass(frozen=True)
class JointScore:
    joint: str
    n: int
    rmse_px: float
    rmse_norm: float
    pck: dict[str, float]
    oks: float
    icc_x: float | None
    icc_y: float | None
    icc: float | None

    def to_dict(self, rank: int | None = None) -> dict:
        payload = {
            "joint": self.joint,
            "n": self.n,
            "rmse_px": round(self.rmse_px, 3),
            "rmse_norm": round(self.rmse_norm, 6),
            "pck": {k: round(v, 4) for k, v in self.pck.items()},
            "oks": round(self.oks, 6),
            "icc_x": None if self.icc_x is None else round(self.icc_x, 6),
            "icc_y": None if self.icc_y is None else round(self.icc_y, 6),
            "icc": None if self.icc is None else round(self.icc, 6),
        }
        if rank is not None:
            payload["rank"] = rank
        return payload


def euclidean(a: Point, b: Point) -> float:
    return sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2)


def paired_distances(
    reference: dict[str, dict[str, Point]],
    candidate: dict[str, dict[str, Point]],
    joint: str,
) -> list[tuple[str, float]]:
    """返回 [(frame, distance)]，只取两侧都存在且可见的帧。"""
    out: list[tuple[str, float]] = []
    for frame in sorted(set(reference) & set(candidate)):
        ref_pt = reference[frame].get(joint)
        cand_pt = candidate[frame].get(joint)
        if ref_pt is None or cand_pt is None:
            continue
        if not ref_pt.visible or not cand_pt.visible:
            continue
        out.append((frame, euclidean(ref_pt, cand_pt)))
    return out


def paired_coordinates(
    reference: dict[str, dict[str, Point]],
    candidate: dict[str, dict[str, Point]],
    joint: str,
) -> list[tuple[float, float, float, float]]:
    """返回 [(ref_x, ref_y, cand_x, cand_y)]，用于 ICC。"""
    out: list[tuple[float, float, float, float]] = []
    for frame in sorted(set(reference) & set(candidate)):
        ref_pt = reference[frame].get(joint)
        cand_pt = candidate[frame].get(joint)
        if ref_pt is None or cand_pt is None:
            continue
        if not ref_pt.visible or not cand_pt.visible:
            continue
        out.append((ref_pt.x, ref_pt.y, cand_pt.x, cand_pt.y))
    return out


def rmse(values: list[float]) -> float:
    if not values:
        return 0.0
    return sqrt(sum(v * v for v in values) / len(values))


def pck(distances: list[float], body_length: float, thresholds=PCK_THRESHOLDS) -> dict[str, float]:
    """PCK@k：距离 ≤ k×体长 的占比。分母只含参与评估的点。"""
    if not distances or body_length <= 0:
        return {f"{t:.2f}": 0.0 for t in thresholds}
    out: dict[str, float] = {}
    for t in thresholds:
        limit = t * body_length
        out[f"{t:.2f}"] = sum(1 for d in distances if d <= limit) / len(distances)
    return out


def bbox_area(reference: dict[str, dict[str, Point]]) -> tuple[float, float, float]:
    """返回 (area, width, height)，基于全部可见点；无可用点时返回 (0,0,0)。"""
    xs: list[float] = []
    ys: list[float] = []
    for points in reference.values():
        for pt in points.values():
            if pt.visible:
                xs.append(pt.x)
                ys.append(pt.y)
    if not xs:
        return 0.0, 0.0, 0.0
    width = max(xs) - min(xs)
    height = max(ys) - min(ys)
    return width * height, width, height


def resolve_area(
    reference: dict[str, dict[str, Point]], body_length: float
) -> tuple[float, str]:
    """确定 OKS 目标面积：优先关键点包围盒，退化则用 (0.5×体长)²。"""
    area, _, _ = bbox_area(reference)
    if area <= 0 or area < (_AREA_MIN_RATIO * body_length) ** 2:
        return (0.5 * body_length) ** 2, "body_length_fallback"
    return area, "keypoint_bbox"


def oks_joint(distances: list[float], area: float, joint: str) -> float:
    """单关节 OKS：exp(-d² / (2·area·σ²)) 的帧均值。

    COCO 标准 OKS 以 ``k = 2σ`` 计入分母，即 ``2·area·(2σ)²``；此处保持与
    COCO 评估脚本一致的 ``2σ`` 约定。
    """
    sigma = COCO17_SIGMAS.get(joint)
    if not distances or area <= 0 or sigma is None:
        return 0.0
    key = 8.0 * area * sigma * sigma  # 2·area·(2σ)²
    return sum(exp(-(d * d) / key) for d in distances) / len(distances)


def icc_2_1(pairs: list[tuple[float, float]]) -> float | None:
    """ICC(2,1)：two-way random effects，absolute agreement，single measure。

    ``pairs`` 为 (rater1, rater2)；subject 为帧。k=2。
    """
    n = len(pairs)
    k = 2
    if n < 2:
        return None
    grand = sum(a + b for a, b in pairs) / (n * k)
    sst = sum((a - grand) ** 2 + (b - grand) ** 2 for a, b in pairs)
    subject_means = [(a + b) / 2 for a, b in pairs]
    ssb = k * sum((m - grand) ** 2 for m in subject_means)
    rater_means = [sum(a for a, _ in pairs) / n, sum(b for _, b in pairs) / n]
    ssr = n * sum((m - grand) ** 2 for m in rater_means)
    sse = sst - ssb - ssr
    if sse < 0:
        sse = 0.0
    msb = ssb / (n - 1)
    msr = ssr / (k - 1)
    mse = sse / ((n - 1) * (k - 1))
    denominator = msb + (k - 1) * mse + k * (msr - mse) / n
    if abs(denominator) < 1e-12:
        return None
    return (msb - mse) / denominator


def score_joint(
    reference: dict[str, dict[str, Point]],
    candidate: dict[str, dict[str, Point]],
    joint: str,
    body_length: float,
    area: float,
) -> JointScore | None:
    dists = paired_distances(reference, candidate, joint)
    if not dists:
        return None
    values = [d for _, d in dists]
    coords = paired_coordinates(reference, candidate, joint)
    icc_x = icc_2_1([(x1, x2) for x1, _, x2, _ in coords])
    icc_y = icc_2_1([(y1, y2) for _, y1, _, y2 in coords])
    icc = None
    if icc_x is not None or icc_y is not None:
        icc = min(v for v in (icc_x, icc_y) if v is not None)
    return JointScore(
        joint=joint,
        n=len(dists),
        rmse_px=rmse(values),
        rmse_norm=rmse(values) / body_length,
        pck=pck(values, body_length),
        oks=oks_joint(values, area, joint),
        icc_x=icc_x,
        icc_y=icc_y,
        icc=icc,
    )


def rank_and_aggregate(scores: list[JointScore]) -> tuple[list[dict], dict]:
    """按 rmse_norm 降序排名，并给出聚合统计与最差三关节。"""
    ordered = sorted(scores, key=lambda s: s.rmse_norm, reverse=True)
    per_joint = [s.to_dict(rank=i + 1) for i, s in enumerate(ordered)]
    norms = sorted(s.rmse_norm for s in scores)
    if norms:
        median_norm = norms[len(norms) // 2] if len(norms) % 2 else (
            norms[len(norms) // 2 - 1] + norms[len(norms) // 2]
        ) / 2
    else:
        median_norm = 0.0
    aggregate = {
        "joints_evaluated": len(scores),
        "rmse_norm_mean": round(sum(norms) / len(norms), 6) if norms else 0.0,
        "rmse_norm_median": round(median_norm, 6),
        "worst_three": [s.joint for s in ordered[:3]],
    }
    return per_joint, aggregate
