"""side_2d_kinematics 质量评估器（独立，对应 design D13 / tasks 10.x）。

**只检查**本计算器依赖的前置条件；**不检查** scale / waterline / events /
distance_markers / swim_direction（那些是旧 side_view_metrics 的关注点）。

issue codes：
- METRIC_SAMPLE_INSUFFICIENT
- SINGLE_SIDE_FALLBACK（按 metric + 连续帧区间聚合，不逐帧）
- REFERENCE_BODY_LENGTH_INSUFFICIENT
- TEMPORAL_CONTINUITY_LOW
- FRAME_MAPPING_UNVERIFIED
- STROKE_CONTEXT_UNKNOWN
- HEAD_POINTS_INSUFFICIENT
- PERIODICITY_PEAK_WEAK
"""

from app.services.metrics.kinematics.frame_resolver import ConstructionMode

ISSUE_METRIC_SAMPLE_INSUFFICIENT = "METRIC_SAMPLE_INSUFFICIENT"
ISSUE_SINGLE_SIDE_FALLBACK = "SINGLE_SIDE_FALLBACK"
ISSUE_REFERENCE_BODY_LENGTH_INSUFFICIENT = "REFERENCE_BODY_LENGTH_INSUFFICIENT"
ISSUE_TEMPORAL_CONTINUITY_LOW = "TEMPORAL_CONTINUITY_LOW"
ISSUE_FRAME_MAPPING_UNVERIFIED = "FRAME_MAPPING_UNVERIFIED"
ISSUE_STROKE_CONTEXT_UNKNOWN = "STROKE_CONTEXT_UNKNOWN"
ISSUE_HEAD_POINTS_INSUFFICIENT = "HEAD_POINTS_INSUFFICIENT"
ISSUE_PERIODICITY_PEAK_WEAK = "PERIODICITY_PEAK_WEAK"

_STROKE_AVAILABLE = {"freestyle"}


class Side2DKinematicsQualityEvaluator:
    """评估 side_2d_kinematics 结果质量，产出结构化 issue 列表。"""

    def evaluate(
        self,
        *,
        summary: dict,
        time_series: dict,
        reference_body_length,
        frames,
        ctx: dict,
    ) -> dict:
        issues: list[dict] = []
        mapping_status = ctx.get("frame_mapping_status", "unknown")
        stroke_type = (ctx.get("stroke_type") or "unknown") or "unknown"

        # ── 参考体长 ──
        rbl = reference_body_length
        if rbl is None or rbl.availability == "unavailable":
            issues.append({
                "code": ISSUE_REFERENCE_BODY_LENGTH_INSUFFICIENT,
                "message": "参考体长样本不足（<3 帧），归一化类指标不可用",
            })
        elif rbl.availability == "low_confidence":
            issues.append({
                "code": ISSUE_REFERENCE_BODY_LENGTH_INSUFFICIENT,
                "message": "参考体长置信度不足（3–7 帧），归一化类指标降级",
            })

        # ── 帧映射 ──
        if mapping_status != "verified":
            issues.append({
                "code": ISSUE_FRAME_MAPPING_UNVERIFIED,
                "message": "帧映射未验证，时序类指标按 annotation_frame 计算，代表性帧不可直接提取",
            })

        # ── 泳姿上下文 ──
        if stroke_type not in _STROKE_AVAILABLE:
            issues.append({
                "code": ISSUE_STROKE_CONTEXT_UNKNOWN,
                "message": f"泳姿={stroke_type}（非 freestyle），周期性指标降级为 low_confidence",
            })

        # ── 头部点 ──
        head_available = sum(1 for f in frames if f.head_center.available)
        if head_available < 3:
            issues.append({
                "code": ISSUE_HEAD_POINTS_INSUFFICIENT,
                "message": "头部关键点可用帧不足，头部/躯干类指标不可用",
            })

        # ── 逐指标 ──
        computed = 0
        skipped = 0
        for key, env in summary.items():
            if env is None:
                continue
            if env.availability == "unavailable":
                skipped += 1
                if env.sample_count == 0:
                    issues.append({
                        "code": ISSUE_METRIC_SAMPLE_INSUFFICIENT,
                        "metric": key,
                        "message": f"指标 {key} 缺少足够样本或必需输入点",
                    })
            else:
                computed += 1
                if env.availability == "low_confidence":
                    details = env.details or {}
                    if details.get("continuity_factor", 1.0) < 0.70:
                        issues.append({
                            "code": ISSUE_TEMPORAL_CONTINUITY_LOW,
                            "metric": key,
                            "message": f"指标 {key} 时序连续性不足",
                        })
                    if key == "kick_periodicity" and details.get("reason") == "weak_or_no_peak":
                        issues.append({
                            "code": ISSUE_PERIODICITY_PEAK_WEAK,
                            "metric": key,
                            "message": "踢腿周期性自相关峰弱或无峰",
                        })

        # ── 单侧回退（按 metric + 连续帧区间聚合）──
        issues.extend(self._aggregate_single_side(time_series))

        # ── level ──
        if rbl is None or rbl.availability == "unavailable" or len(frames) == 0:
            level = "error"
        elif issues:
            level = "warning"
        else:
            level = "good"

        return {
            "level": level,
            "issues": issues,
            "computed_metric_count": computed,
            "skipped_metric_count": skipped,
            "reference_body_length": rbl.model_dump() if rbl else None,
            "frame_mapping_status": mapping_status,
            "stroke_type": stroke_type,
        }

    def _aggregate_single_side(self, time_series: dict) -> list[dict]:
        """扫描 time_series，按 metric + 连续帧区间聚合单侧回退。"""
        out: list[dict] = []
        for metric_key, series in time_series.items():
            if not isinstance(series, list):
                continue
            start = None
            prev_frame = None
            for p in series:
                mode = p.get("construction_mode")
                is_single = mode in (ConstructionMode.LEFT_PROXY.value, ConstructionMode.RIGHT_PROXY.value)
                if is_single:
                    fno = p.get("annotation_frame")
                    if start is None:
                        start = fno
                        prev_frame = fno
                    elif prev_frame is not None and fno is not None and fno == prev_frame + 1:
                        prev_frame = fno
                    else:
                        out.append(self._single_side_issue(metric_key, start, prev_frame))
                        start = fno
                        prev_frame = fno
                else:
                    if start is not None:
                        out.append(self._single_side_issue(metric_key, start, prev_frame))
                        start = None
                        prev_frame = None
            if start is not None:
                out.append(self._single_side_issue(metric_key, start, prev_frame))
        return out

    def _single_side_issue(self, metric_key, start, end) -> dict:
        return {
            "code": ISSUE_SINGLE_SIDE_FALLBACK,
            "metric": metric_key,
            "frame_range": [start, end],
            "message": f"指标 {metric_key} 在帧区间 [{start}, {end}] 使用单侧代理点",
        }
