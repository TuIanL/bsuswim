"""几何工具：点/向量/角度/距离/线段投影。

关键点统一用 ``(x, y)`` 元组参与计算。``_as_xy`` 负责把标注里的点节点
（dict ``{x, y, confidence, visibility}`` 或 pydantic ``KeypointPoint``）规整成
元组；``visibility == "missing"`` 或缺少坐标时返回 ``None``，供调用方跳过。
"""

from math import acos, atan2, cos, degrees, hypot, radians, sin, sqrt

CORE_KEYPOINTS: tuple[str, ...] = ("shoulder", "elbow", "wrist", "hip", "knee", "ankle")


def _as_xy(point) -> tuple[float, float] | None:
    """把点节点规整成 (x, y)；不可用时返回 None。"""
    if point is None:
        return None
    if isinstance(point, dict):
        if point.get("visibility") == "missing":
            return None
        x = point.get("x")
        y = point.get("y")
        if x is None or y is None:
            return None
        return float(x), float(y)
    if isinstance(point, (tuple, list)) and len(point) >= 2:
        try:
            return float(point[0]), float(point[1])
        except (TypeError, ValueError):
            return None
    # pydantic-like：KeypointPoint 等
    x = getattr(point, "x", None)
    y = getattr(point, "y", None)
    if x is None or y is None:
        return None
    return float(x), float(y)


def distance_px(p1, p2) -> float | None:
    """两点像素距离。任一点不可用返回 None。"""
    a = _as_xy(p1)
    b = _as_xy(p2)
    if a is None or b is None:
        return None
    return hypot(a[0] - b[0], a[1] - b[1])


def distance_cm(p1, p2, pixels_per_meter: float | None) -> float | None:
    """两点真实距离（cm）。缺 ppm 或任一点不可用返回 None。"""
    if not pixels_per_meter:
        return None
    d = distance_px(p1, p2)
    if d is None:
        return None
    return d / pixels_per_meter * 100.0


def angle_between_points(a, b, c) -> float | None:
    """返回 ∠ABC（度数，0–180）。任一顶点不可用返回 None。"""
    A = _as_xy(a)
    B = _as_xy(b)
    C = _as_xy(c)
    if A is None or B is None or C is None:
        return None
    v1 = (A[0] - B[0], A[1] - B[1])
    v2 = (C[0] - B[0], C[1] - B[1])
    m1 = hypot(*v1)
    m2 = hypot(*v2)
    if m1 == 0 or m2 == 0:
        return None
    cos_theta = (v1[0] * v2[0] + v1[1] * v2[1]) / (m1 * m2)
    cos_theta = max(-1.0, min(1.0, cos_theta))
    return degrees(acos(cos_theta))


def angle_to_horizontal(p1, p2) -> float | None:
    """线段 p1→p2 与水平线的夹角（绝对值，0–90）。图像 y 轴向下，取 abs 修正方向。"""
    a = _as_xy(p1)
    b = _as_xy(p2)
    if a is None or b is None:
        return None
    dx = b[0] - a[0]
    dy = b[1] - a[1]
    return abs(degrees(atan2(dy, dx)))


def project_point_to_line(point, line_start, line_end) -> tuple[float, float] | None:
    """把点投影到线段所在直线，返回投影点坐标。"""
    p = _as_xy(point)
    s = _as_xy(line_start)
    e = _as_xy(line_end)
    if p is None or s is None or e is None:
        return None
    dx = e[0] - s[0]
    dy = e[1] - s[1]
    length_sq = dx * dx + dy * dy
    if length_sq == 0:
        return s
    t = ((p[0] - s[0]) * dx + (p[1] - s[1]) * dy) / length_sq
    return (s[0] + t * dx, s[1] + t * dy)


def vertical_distance_to_line(point, line_start, line_end) -> float | None:
    """点到线段所在直线的垂直距离（像素）。"""
    p = _as_xy(point)
    s = _as_xy(line_start)
    e = _as_xy(line_end)
    if p is None or s is None or e is None:
        return None
    proj = project_point_to_line(p, s, e)
    if proj is None:
        return None
    return hypot(p[0] - proj[0], p[1] - proj[1])


def waterline_y_at_x(waterline: dict, x: float) -> float | None:
    """给定水面线（``{"points": [[x1,y1],[x2,y2]]}``）与 x，线性插值返回水面 y。"""
    if not waterline:
        return None
    pts = waterline.get("points")
    if not pts or len(pts) < 2:
        return None
    (x1, y1), (x2, y2) = pts[0], pts[1]
    if x2 == x1:
        return float(y1)
    t = (x - x1) / (x2 - x1)
    return y1 + t * (y2 - y1)


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def has_required_points(points: dict, required: tuple[str, ...]) -> bool:
    """检查给定帧的 points 是否覆盖全部 required 关键点（且均可用）。"""
    return all(_as_xy(points.get(name)) is not None for name in required)
