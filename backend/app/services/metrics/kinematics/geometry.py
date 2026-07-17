"""side_2d_kinematics 专用几何与统计工具。

与旧 ``app.services.metrics.geometry`` 完全解耦：本模块**不修改**旧的
``angle_to_horizontal()``，新增独立的带符号倾角 / 统计 / 相关 / 尖峰检测工具，
所有输出保证**不出现 NaN / Inf**（缺数据返回 None，数值 safe）。

关键点统一用 ``(x, y)`` 元组参与计算。``_as_xy`` 负责把标注里的点节点
（dict ``{x, y, confidence, visibility}`` 或 pydantic ``KeypointPoint``）规整成
元组；``visibility == "missing"`` 或缺少坐标时返回 ``None``，供调用方跳过。
"""

from math import atan2, degrees, hypot
from statistics import mean, median, pstdev
from typing import Sequence

EPS = 1e-9


def _safe(v: float) -> float | None:
    """把非有限值规整为 None，保证 JSON 安全。"""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        if v != v or v in (float("inf"), float("-inf")):  # NaN / Inf
            return None
        return float(v)
    return None


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
    x = getattr(point, "x", None)
    y = getattr(point, "y", None)
    if x is None or y is None:
        return None
    return float(x), float(y)


# ── 角度 ──


def signed_line_tilt_deg(p1, p2) -> float | None:
    """线段 p1→p2 与水平线的**带符号**倾角，范围 ``[-90°, 90°)``。

    屏幕 y 轴向下。``atan2(dy, dx)`` 给出 ``(-180°, 180°]``，
    折叠到 ``[-90°, 90°)``。两点重合返回 None。
    """
    a = _as_xy(p1)
    b = _as_xy(p2)
    if a is None or b is None:
        return None
    dx = b[0] - a[0]
    dy = b[1] - a[1]
    if abs(dx) < EPS and abs(dy) < EPS:
        return None
    theta = degrees(atan2(dy, dx))
    return ((theta + 90.0) % 180.0) - 90.0


def line_angle_to_screen_horizontal_deg(p1, p2) -> float | None:
    """线段与屏幕水平的**无方向锐角**，范围 ``0–90°``。"""
    theta = signed_line_tilt_deg(p1, p2)
    if theta is None:
        return None
    return abs(theta)


def angle_between_points(a, b, c) -> float | None:
    """∠ABC（度数，0–180）。任一顶点不可用返回 None。"""
    A = _as_xy(a)
    B = _as_xy(b)
    C = _as_xy(c)
    if A is None or B is None or C is None:
        return None
    v1 = (A[0] - B[0], A[1] - B[1])
    v2 = (C[0] - B[0], C[1] - B[1])
    m1 = hypot(*v1)
    m2 = hypot(*v2)
    if m1 < EPS or m2 < EPS:
        return None
    cos_theta = (v1[0] * v2[0] + v1[1] * v2[1]) / (m1 * m2)
    cos_theta = max(-1.0, min(1.0, cos_theta))
    from math import acos

    return degrees(acos(cos_theta))


# ── 向量 / 中点 ──


def distance_px(p1, p2) -> float | None:
    """两点像素距离。任一点不可用返回 None。"""
    a = _as_xy(p1)
    b = _as_xy(p2)
    if a is None or b is None:
        return None
    return hypot(a[0] - b[0], a[1] - b[1])


def vector(p1, p2) -> tuple[float, float] | None:
    """从 p1 指向 p2 的向量。任一不可用返回 None。"""
    a = _as_xy(p1)
    b = _as_xy(p2)
    if a is None or b is None:
        return None
    return (b[0] - a[0], b[1] - a[1])


def midpoint(p1, p2) -> tuple[float, float] | None:
    """两点的中点。任一不可用返回 None。"""
    a = _as_xy(p1)
    b = _as_xy(p2)
    if a is None or b is None:
        return None
    return ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)


# ── 百分位 / 稳健 ROM ──


def percentile(values: Sequence[float], q: float) -> float | None:
    """线性插值百分位（q ∈ [0, 100]）。样本不足返回 None。"""
    vals = [v for v in values if v is not None]
    if len(vals) < 1:
        return None
    if len(vals) == 1:
        return float(vals[0])
    s = sorted(vals)
    if q <= 0:
        return float(s[0])
    if q >= 100:
        return float(s[-1])
    pos = (len(s) - 1) * (q / 100.0)
    lo = int(pos)
    hi = min(lo + 1, len(s) - 1)
    frac = pos - lo
    return s[lo] + (s[hi] - s[lo]) * frac


def robust_rom_p95_p05(values: Sequence[float]) -> float | None:
    """稳健极差 P95 − P05（度数/像素）。样本不足返回 None。"""
    p95 = percentile(values, 95)
    p05 = percentile(values, 5)
    if p95 is None or p05 is None:
        return None
    rom = p95 - p05
    return _safe(rom)


# ── 标准差 / 变异系数 ──


def std_dev(values: Sequence[float]) -> float | None:
    vals = [v for v in values if v is not None]
    if len(vals) < 2:
        return None
    return _safe(pstdev(vals))


def coefficient_of_variation_pct(values: Sequence[float], guard_mean_min: float = 1.0) -> float | None:
    """变异系数 % = 100 × std / |mean|。

    ``|mean| < guard_mean_min`` 时返回 None（mean 太小，CV 无意义；
    退化场景由调用方据此标记 low_confidence）。
    """
    vals = [v for v in values if v is not None]
    if len(vals) < 2:
        return None
    m = mean(vals)
    if abs(m) < guard_mean_min:
        return None
    s = pstdev(vals)
    return _safe(100.0 * s / abs(m))


# ── 相关 ──


def pearson_correlation(x: Sequence[float], y: Sequence[float]) -> float | None:
    """Pearson 相关系数。长度或方差不足返回 None。"""
    xs = [v for v in x if v is not None]
    ys = [v for v in y if v is not None]
    if len(xs) < 2 or len(ys) < 2:
        return None
    n = min(len(xs), len(ys))
    xs = xs[:n]
    ys = ys[:n]
    mx = mean(xs)
    my = mean(ys)
    num = sum((xs[i] - mx) * (ys[i] - my) for i in range(n))
    dx = sum((xs[i] - mx) ** 2 for i in range(n))
    dy = sum((ys[i] - my) ** 2 for i in range(n))
    denom = (dx * dy) ** 0.5
    if denom < EPS:
        return None
    return _safe(num / denom)


def _zero_mean_series(values: Sequence[float]) -> list[float] | None:
    vals = [v for v in values if v is not None]
    if len(vals) < 2:
        return None
    m = mean(vals)
    return [v - m for v in vals]


def autocorrelation_series(values: Sequence[float], max_lag: int) -> list[float] | None:
    """零均值无偏归一化自相关序列（索引 = lag，r[0] = 1.0）。返回 None 表示样本不足。"""
    z = _zero_mean_series(values)
    if z is None:
        return None
    n = len(z)
    if max_lag < 1 or max_lag >= n:
        return None
    var = sum(v * v for v in z) / n
    if var < EPS:
        return None
    out: list[float] = []
    for k in range(1, max_lag + 1):
        cov = sum(z[i] * z[i + k] for i in range(n - k)) / (n - k)
        out.append(_safe(cov / var))
    return out


def best_period_from_autocorr(
    series: Sequence[float],
    lag_range: tuple[int, int],
    min_contig: int = 24,
    peak_threshold: float = 0.30,
) -> tuple[int | None, float | None]:
    """从自相关序列中选取主周期。

    :return: (period_frames, score)；无有效峰返回 (None, None)。
    规则：在 lag_range 内选局部最大且 ``>= peak_threshold`` 的峰；
    多个峰时取 lag 最小、相关性最大的峰。
    """
    lo, hi = lag_range
    if hi < lo:
        lo, hi = hi, lo
    ac = autocorrelation_series(series, hi)
    if ac is None:
        return None, None
    best_lag: int | None = None
    best_corr: float | None = None
    for lag in range(max(lo, 1), hi + 1):
        if lag - 1 >= len(ac):
            break
        c = ac[lag - 1]
        if c is None or c < peak_threshold:
            continue
        # 局部最大：比相邻 lag 都高
        left = ac[lag - 2] if lag - 2 >= 0 else None
        right = ac[lag] if lag < len(ac) else None
        if left is not None and c < left:
            continue
        if right is not None and c < right:
            continue
        if best_corr is None or c > best_corr or (abs(c - (best_corr or 0)) < EPS and (best_lag is None or lag < best_lag)):
            best_lag = lag
            best_corr = c
    return (_safe(best_lag), _safe(best_corr))


def cross_correlation_lag(
    a: Sequence[float],
    b: Sequence[float],
    lag_range: tuple[int, int],
    max_abs_lag: int | None = None,
) -> tuple[int | None, float | None]:
    """求使 b 相对 a 对齐的最佳整数 lag。

    ``lag > 0`` 表示 b 滞后于 a；``lag < 0`` 表示 b 领先 a。
    使用零均值归一化互相关，选相关性最大的 lag（平局取 lag 最小）。

    :param max_abs_lag: 若给定，搜索窗口被限制在 ``[-max_abs_lag, +max_abs_lag]``
        内（锚定在 0 附近，即一个周期内），用于避免周期性信号的整周期别名。
        此时忽略 ``lag_range`` 的上下界。
    """
    za = _zero_mean_series(a)
    zb = _zero_mean_series(b)
    if za is None or zb is None:
        return None, None
    if max_abs_lag is not None and max_abs_lag > 0:
        lo, hi = -max_abs_lag, max_abs_lag
    else:
        lo, hi = lag_range
    best_lag: int | None = None
    best_corr: float | None = None
    for lag in range(lo, hi + 1):
        if lag >= 0:
            n = len(za) - lag
            if n < 2:
                continue
            xa = za[:n]
            xb = zb[lag : lag + n]
        else:
            m = -lag
            n = len(za) - m
            if n < 2:
                continue
            xa = za[m : m + n]
            xb = zb[:n]
        if len(xa) != len(xb) or len(xa) < 2:
            continue
        c = pearson_correlation(xa, xb)
        if c is None:
            continue
        if best_corr is None or c > best_corr:
            best_lag = lag
            best_corr = c
    return (_safe(best_lag), _safe(best_corr))


# ── MAD 速度尖峰检测 ──


def _mad(values: Sequence[float]) -> float | None:
    if len(values) < 1:
        return None
    med = median(values)
    return median([abs(v - med) for v in values])


def mad_velocity_spikes(
    values: Sequence[float],
    threshold: float = 3.5,
) -> list[int]:
    """对相邻帧差分（速度）做 MAD 稳健 z-score 检测。

    :return: 速度序列中 ``|z| >= threshold`` 的索引列表（即尖峰所在位置）。
    样本不足返回空列表。
    """
    vals = [v for v in values if v is not None]
    if len(vals) < 4:
        return []
    velocities = [vals[i + 1] - vals[i] for i in range(len(vals) - 1)]
    med = median(velocities)
    mad = _mad(velocities)
    if mad is None or mad < EPS:
        # 退化：用标准差兜底，避免全 0 误报
        s = pstdev(velocities)
        if s < EPS:
            return []
        scale = 0.6745 / s
        spikes = [i for i, v in enumerate(velocities) if abs(0.6745 * (v - med) / s) >= threshold]
        return spikes
    scale = 0.6745 / mad
    spikes = [i for i, v in enumerate(velocities) if abs(0.6745 * (v - med) / mad) >= threshold]
    return spikes


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))
