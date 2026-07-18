"""证据帧解析器（EvidenceResolver）。

设计约束（R3）：
- 优先使用 ``AnnotationMetric.metrics.time_series`` 定位证据帧。
- 当所需位置序列未持久化时（如 KRF002 髋中点 y），MAY 从 ``CanonicalKinematicFrame``
  重建该序列以定位证据帧，但 MUST NOT 重新计算或覆盖触发规则的指标值。
- 即使 source-video mapping 未验证，也保留 annotation_frame，并标记 extractable=False。
- 每条 finding 证据帧上限为 3。
"""

from typing import Any

from app.schemas.kinematic_review_finding import FindingEvidenceFrame

# 时间序列键 → 证据帧选择策略
_RESOLVERS: dict[str, str] = {
    "body_axis_max_deviation": "body_axis_angle_deg",
    "knee_minimum_triggering_side": "knee",
    "ankle_peak_trough": "ankle_vertical_range_px",
    "head_spike_first_n": "head_motion_spike",
    "head_trunk_sync_max": "head_trunk",
}


def _series_get(metric_dict: dict[str, Any], key: str) -> list[dict]:
    ts = metric_dict.get("time_series") or {}
    return ts.get(key) or []


def _sample_to_frame(
    sample: dict, metric_key: str, role: str, mapping_status: str = "unknown"
) -> FindingEvidenceFrame:
    sv = sample.get("source_video_frame")
    extractable = sv is not None and mapping_status == "verified"
    return FindingEvidenceFrame(
        metric_key=metric_key,
        annotation_frame=sample.get("annotation_frame") if sample.get("annotation_frame") is not None else sample.get("frame", 0),
        source_video_frame=sv,
        time_sec=sample.get("time_sec"),
        role=role,
        value=sample.get("value"),
        extractable=extractable,
        mapping_status=mapping_status if mapping_status != "unknown" else (sample.get("mapping_status") or "unknown"),
    )


def _frame_from_canonical(f, metric_key: str, role: str, mapping_status: str = "unknown") -> FindingEvidenceFrame:
    sv = f.source_video_frame
    extractable = sv is not None and mapping_status == "verified"
    return FindingEvidenceFrame(
        metric_key=metric_key,
        annotation_frame=f.annotation_frame if f.annotation_frame is not None else f.frame_index,
        source_video_frame=sv,
        time_sec=f.time_sec,
        role=role,
        extractable=extractable,
        mapping_status=mapping_status if mapping_status != "unknown" else "unknown",
    )


class EvidenceResolver:
    """定位证据帧；不重算触发值。"""

    def __init__(
        self,
        metric_dict: dict[str, Any],
        canonical_frames: list | None = None,
        mapping_status: str = "unknown",
    ):
        self.metric_dict = metric_dict or {}
        self.canonical_frames = canonical_frames or []
        self.mapping_status = mapping_status

    def resolve(self, resolver_name: str, limit: int = 3) -> list[FindingEvidenceFrame]:
        limit = min(max(limit, 1), 3)
        fn = getattr(self, f"_r_{resolver_name}", None)
        if fn is None:
            return []
        frames = fn()
        # 去重（按 annotation_frame + role）
        seen = set()
        out: list[FindingEvidenceFrame] = []
        for fr in frames:
            key = (fr.annotation_frame, fr.role)
            if key in seen:
                continue
            seen.add(key)
            out.append(fr)
            if len(out) >= limit:
                break
        return out

    # ── KRF001：身体轴角偏离中位数最大的帧 ──

    def _r_body_axis_max_deviation(self) -> list[FindingEvidenceFrame]:
        ts = _series_get(self.metric_dict, "body_axis_angle_deg")
        return self._extreme_deviation(ts, "body_axis_angle_deg", "max_deviation")

    # ── KRF002：髋中点最高/最低帧（需回读标注重建）──

    def _r_hip_high_low(self) -> list[FindingEvidenceFrame]:
        frames = [f for f in self.canonical_frames if f.hip_mid.available and f.hip_mid.y is not None]
        if not frames:
            return []
        hi = max(frames, key=lambda f: f.hip_mid.y)
        lo = min(frames, key=lambda f: f.hip_mid.y)
        return [
            _frame_from_canonical(hi, "hip_mid_y", "maximum", self.mapping_status),
            _frame_from_canonical(lo, "hip_mid_y", "minimum", self.mapping_status),
        ]

    # ── KRF003：触发侧肘角最小/最大帧 ──

    def _r_elbow_min_max_triggering_side(self) -> list[FindingEvidenceFrame]:
        left = _series_get(self.metric_dict, "left_elbow_angle_deg")
        right = _series_get(self.metric_dict, "right_elbow_angle_deg")
        out: list[FindingEvidenceFrame] = []
        for ts, side in ((left, "left"), (right, "right")):
            if not ts:
                continue
            mn = min(ts, key=lambda p: p.get("value") if p.get("value") is not None else float("inf"))
            mx = max(ts, key=lambda p: p.get("value") if p.get("value") is not None else float("-inf"))
            out.append(_sample_to_frame(mn, f"{side}_elbow_angle_deg", "minimum", self.mapping_status))
            out.append(_sample_to_frame(mx, f"{side}_elbow_angle_deg", "maximum", self.mapping_status))
        return out

    # ── KRF004：左右侧各自 ROM 边界帧 ──

    def _r_elbow_asymmetry_bounds(self) -> list[FindingEvidenceFrame]:
        # 复用肘极值帧即可表达左右 ROM 边界
        return self._r_elbow_min_max_triggering_side()

    # ── KRF005：触发侧膝角最小帧 ──

    def _r_knee_minimum_triggering_side(self) -> list[FindingEvidenceFrame]:
        left = _series_get(self.metric_dict, "left_knee_angle_deg")
        right = _series_get(self.metric_dict, "right_knee_angle_deg")
        best = None
        best_side = None
        for ts, side in ((left, "left"), (right, "right")):
            if not ts:
                continue
            mn = min(ts, key=lambda p: p.get("value") if p.get("value") is not None else float("inf"))
            if best is None or (mn.get("value") is not None and best.get("value") is not None and mn["value"] < best["value"]):
                best = mn
                best_side = side
        if best is None:
            return []
        return [_sample_to_frame(best, f"{best_side}_knee_angle_deg", "minimum", self.mapping_status)]

    # ── KRF006：踝部相对轨迹的相邻峰值和谷值 ──

    def _r_ankle_peak_trough(self) -> list[FindingEvidenceFrame]:
        ts = _series_get(self.metric_dict, "ankle_vertical_range_px")
        if not ts:
            return []
        vals = [p.get("value") for p in ts if p.get("value") is not None]
        if not vals:
            return []
        hi = max(ts, key=lambda p: p.get("value") if p.get("value") is not None else float("-inf"))
        lo = min(ts, key=lambda p: p.get("value") if p.get("value") is not None else float("inf"))
        return [
            _sample_to_frame(hi, "ankle_vertical_range_px", "peak", self.mapping_status),
            _sample_to_frame(lo, "ankle_vertical_range_px", "trough", self.mapping_status),
        ]

    # ── KRF007：头部尖峰前 N 帧 ──

    def _r_head_spike_first_n(self) -> list[FindingEvidenceFrame]:
        details = (self.metric_dict.get("summary") or {}).get("head_motion_spike_frames")
        if isinstance(details, dict):
            frames = details.get("details", {}).get("spike_annotation_frames") or []
        elif hasattr(details, "details"):
            frames = getattr(details.details, "spike_annotation_frames", []) or []
        else:
            frames = []
        out: list[FindingEvidenceFrame] = []
        ts = _series_get(self.metric_dict, "head_vertical_range_px")
        by_ann = {p.get("annotation_frame"): p for p in ts}
        for af in frames[:3]:
            p = by_ann.get(af)
            if p is not None:
                out.append(_sample_to_frame(p, "head_vertical_range_px", "spike", self.mapping_status))
        return out

    # ── KRF008：头部与躯干一阶位移同时最大的帧 ──

    def _r_head_trunk_sync_max(self) -> list[FindingEvidenceFrame]:
        head_ts = _series_get(self.metric_dict, "head_vertical_range_px")
        trunk_ts = _series_get(self.metric_dict, "trunk_vertical_stability")
        if not head_ts or not trunk_ts:
            return []
        by_ann = {p.get("annotation_frame"): p for p in trunk_ts}
        best = None
        best_combined = None
        for hp in head_ts:
            tp = by_ann.get(hp.get("annotation_frame"))
            if tp is None or hp.get("value") is None or tp.get("value") is None:
                continue
            combined = abs(hp["value"]) + abs(tp["value"])
            if best_combined is None or combined > best_combined:
                best_combined = combined
                best = hp
        if best is None:
            return []
        return [_sample_to_frame(best, "head_vertical_range_px", "max_deviation", self.mapping_status)]

    # ── 工具：偏离中位数最大 ──

    @staticmethod
    def _extreme_deviation(ts: list[dict], metric_key: str, role: str) -> list[FindingEvidenceFrame]:
        valid = [p for p in ts if p.get("value") is not None]
        if len(valid) < 2:
            if valid:
                return [_sample_to_frame(valid[0], metric_key, role, "unknown")]
            return []
        vals = [p["value"] for p in valid]
        med = sorted(vals)[len(vals) // 2]
        dev = max(valid, key=lambda p: abs(p["value"] - med))
        return [_sample_to_frame(dev, metric_key, role, "unknown")]
