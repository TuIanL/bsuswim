"""序列连续性因子（对应 design D9 / tasks 5.x）。

三类因子的统一实现：
- 静态帧指标（角度均值、ROM）：continuity_factor = 1.0（不惩罚）
- 相邻差分指标（速度）：valid_delta_count / expected_delta_count
- 序列型指标（周期、同步）：longest_valid_contiguous_run / total_valid_sample_count

expected_frame_step 来自 verified frame mapping；未验证时默认 1。
"""

from statistics import median

from app.services.metrics.kinematics.geometry import clamp


def expected_frame_step(frame_mapping: dict | None) -> int:
    """从 verified frame mapping 推导期望帧步长；无映射或未验证返回 1。"""
    if not frame_mapping:
        return 1
    if not frame_mapping.get("verified", False):
        return 1
    stride = frame_mapping.get("source_frame_stride")
    if stride and stride > 0:
        return int(stride)
    entries = frame_mapping.get("entries") or []
    if len(entries) >= 2:
        svf = [
            e.get("source_video_frame")
            for e in entries
            if isinstance(e, dict) and e.get("source_video_frame") is not None
        ]
        if len(svf) >= 2:
            deltas = [svf[i] - svf[i - 1] for i in range(1, len(svf)) if svf[i] - svf[i - 1] > 0]
            if deltas:
                m = median(deltas)
                if m and m > 0:
                    return int(m)
    return 1


def continuity_factor_static() -> float:
    """静态逐帧汇总：不施加连续性惩罚。"""
    return 1.0


def continuity_factor_delta(valid_deltas: int, expected_deltas: int) -> float:
    """速度类差分指标连续性：有效差分 / 期望差分。"""
    if expected_deltas <= 0:
        return 0.0
    return clamp(valid_deltas / expected_deltas, 0.0, 1.0)


def longest_contiguous_run_length(valid_flags: list[bool]) -> int:
    """最长连续有效段长度。"""
    best = 0
    cur = 0
    for f in valid_flags:
        if f:
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return best


def continuity_factor_sequence(valid_flags: list[bool]) -> float:
    """序列型指标连续性：最长连续有效段 / 总有效样本数。"""
    total = sum(1 for f in valid_flags if f)
    if total <= 0:
        return 0.0
    return clamp(longest_contiguous_run_length(valid_flags) / total, 0.0, 1.0)
