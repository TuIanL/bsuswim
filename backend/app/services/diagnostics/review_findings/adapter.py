"""Side2DKinematicsReviewAdapter：把 ``swim-side-kinematics.v1`` 的 AnnotationMetric
适配为复核引擎的稳定输入。

设计约束（Decision 1b）：
- 不直接消费 ``MetricEnvelope`` 内部键，而是展平为稳定标量上下文。
- 返回 ``ReviewAdapterResult``：``evaluation_context`` 供结构化条件评估器使用，
  ``metric_meta`` 承载溯源 / 可用性 / 置信度，供 evidence / confidence / limitations 构建。
- 派生指标（如 ``hip_vertical_range_ratio``）保留来源键、可用性（取最差）与置信度（取最小）。
- 固定像素阈值不得用于规则；像素波动一律经参考体长归一化。
"""

from typing import Any

from app.schemas.metrics import MetricEnvelope
from app.services.diagnostics.models import DiagnosticMetricsContext

# 派生指标可用性/置信度传播
_AVAIL_ORDER = {"unavailable": 0, "low_confidence": 1, "available": 2}
_AVAIL_RANK = {0: "unavailable", 1: "low_confidence", 2: "available"}


def _worst_availability(avails: list[str]) -> str:
    rank = min((_AVAIL_ORDER.get(a, 0) for a in avails), default=0)
    return _AVAIL_RANK[rank]


def _min_confidence(confs: list[float]) -> float:
    vals = [c for c in confs if c is not None]
    return round(min(vals), 3) if vals else 0.0


class ReviewMetricMeta:
    """单派生/来源指标的质量与溯源元信息。"""

    def __init__(
        self,
        key: str,
        source_metric_keys: list[str],
        value: Any,
        unit: str | None,
        availability: str,
        confidence: float,
        derivation: str | None = None,
        reference_basis: str | None = None,
    ):
        self.key = key
        self.source_metric_keys = source_metric_keys
        self.value = value
        self.unit = unit
        self.availability = availability
        self.confidence = confidence
        self.derivation = derivation
        self.reference_basis = reference_basis


class ReviewAdapterResult:
    def __init__(
        self,
        evaluation_context: DiagnosticMetricsContext,
        metric_meta: dict[str, ReviewMetricMeta],
        warnings: list[str] | None = None,
    ):
        self.evaluation_context = evaluation_context
        self.metric_meta = metric_meta
        self.warnings = warnings or []


def _env(summary: dict, key: str) -> MetricEnvelope | None:
    v = summary.get(key)
    if isinstance(v, MetricEnvelope):
        return v
    if isinstance(v, dict):
        try:
            return MetricEnvelope(**v)
        except Exception:
            return None
    return None


def _scalar(env: MetricEnvelope | None) -> float | int | None:
    if env is None:
        return None
    return env.value


class Side2DKinematicsReviewAdapter:
    """将 side_2d_kinematics 产物适配为复核引擎稳定输入。"""

    def adapt(self, metrics_dict: dict[str, Any]) -> ReviewAdapterResult:
        metrics_dict = metrics_dict or {}
        summary = metrics_dict.get("summary") or {}
        ranges = metrics_dict.get("ranges") or {}
        time_series = metrics_dict.get("time_series") or {}
        ref = metrics_dict.get("reference_body_length") or {}

        flat: dict[str, Any] = {}
        meta: dict[str, ReviewMetricMeta] = {}
        warnings: list[str] = []

        # ── 直接透传的标量 envelope ──
        self._add_scalar(summary, "body_angle_std_deg", flat, meta, unit="deg")
        self._add_scalar(summary, "posture_stability_cv", flat, meta, unit="%")
        self._add_scalar(summary, "head_body_synchrony", flat, meta, unit="r")
        self._add_scalar(summary, "head_vertical_range_px", flat, meta, unit="px")

        # ── 肘 ROM 细节展平 ──
        elbow = _env(summary, "elbow_rom_deg")
        elbow_details = elbow.details if elbow else {}
        for side in ("left", "right", "combined"):
            v = elbow_details.get(side)
            if v is not None:
                key = f"elbow_rom_{side}_deg"
                flat[key] = v
                src = "summary.elbow_rom_deg.details." + side
                meta[key] = ReviewMetricMeta(
                    key=key,
                    source_metric_keys=[src],
                    value=v,
                    unit="deg",
                    availability=elbow.availability if elbow else "unavailable",
                    confidence=elbow.confidence if elbow else 0.0,
                    derivation=f"elbow_rom_deg.details.{side}",
                    reference_basis="joint_geometry",
                )

        # ── 肘左右不对称（度 / 比率）──
        lvr = flat.get("elbow_rom_left_deg")
        rvr = flat.get("elbow_rom_right_deg")
        if lvr is not None and rvr is not None:
            diff = abs(lvr - rvr)
            ratio = (diff / max(lvr, rvr)) if max(lvr, rvr) else 0.0
            flat["elbow_rom_asymmetry_deg"] = round(diff, 2)
            flat["elbow_rom_asymmetry_ratio"] = round(ratio, 3)
            srcs = [
                "summary.elbow_rom_deg.details.left",
                "summary.elbow_rom_deg.details.right",
            ]
            for dkey, dval, derv in (
                ("elbow_rom_asymmetry_deg", round(diff, 2), "abs(left - right)"),
                ("elbow_rom_asymmetry_ratio", round(ratio, 3), "abs(left-right) / max(left,right)"),
            ):
                meta[dkey] = ReviewMetricMeta(
                    key=dkey,
                    source_metric_keys=srcs,
                    value=dval,
                    unit="deg" if "ratio" not in dkey else "ratio",
                    availability=_worst_availability(
                        [meta["elbow_rom_left_deg"].availability, meta["elbow_rom_right_deg"].availability]
                    ),
                    confidence=_min_confidence(
                        [meta["elbow_rom_left_deg"].confidence, meta["elbow_rom_right_deg"].confidence]
                    ),
                    derivation=derv,
                    reference_basis="joint_geometry",
                )

        # ── 膝 P05 展平 + 最小侧 ──
        for side in ("left", "right"):
            r = ranges.get(f"{side}_knee_angle_deg")
            p05 = r.get("p05") if isinstance(r, dict) else getattr(r, "p05", None) if r is not None else None
            if p05 is not None:
                key = f"{side}_knee_p05_deg"
                flat[key] = p05
                meta[key] = ReviewMetricMeta(
                    key=key,
                    source_metric_keys=[f"ranges.{side}_knee_angle_deg.p05"],
                    value=p05,
                    unit="deg",
                    availability="available",
                    confidence=1.0,
                    derivation=f"ranges.{side}_knee_angle_deg.p05",
                    reference_basis="joint_geometry",
                )
        lk = flat.get("left_knee_p05_deg")
        rk = flat.get("right_knee_p05_deg")
        if lk is not None and rk is not None:
            flat["minimum_knee_p05_deg"] = min(lk, rk)
            meta["minimum_knee_p05_deg"] = ReviewMetricMeta(
                key="minimum_knee_p05_deg",
                source_metric_keys=["ranges.left_knee_angle_deg.p05", "ranges.right_knee_angle_deg.p05"],
                value=min(lk, rk),
                unit="deg",
                availability=_worst_availability(
                    [meta["left_knee_p05_deg"].availability, meta["right_knee_p05_deg"].availability]
                ),
                confidence=_min_confidence(
                    [meta["left_knee_p05_deg"].confidence, meta["right_knee_p05_deg"].confidence]
                ),
                derivation="min(left, right)",
                reference_basis="joint_geometry",
            )

        # ── 踢腿周期性：分数 + 周期 + 可评估/峰检测 ──
        kick = _env(summary, "kick_periodicity")
        kick_details = kick.details if kick else {}
        kick_value = kick.value if kick else None
        kick_score = None
        kick_period = None
        if isinstance(kick_value, dict):
            kick_score = kick_value.get("score")
            kick_period = kick_value.get("period_frames")
        sample_count = kick.sample_count if kick else 0
        if kick_score is not None:
            flat["kick_periodicity_score"] = kick_score
            meta["kick_periodicity_score"] = ReviewMetricMeta(
                key="kick_periodicity_score",
                source_metric_keys=["summary.kick_periodicity.value.score"],
                value=kick_score,
                unit="score",
                availability=kick.availability if kick else "unavailable",
                confidence=kick.confidence if kick else 0.0,
                derivation="kick_periodicity.value.score",
                reference_basis="frame_sequence",
            )
        if kick_period is not None:
            flat["kick_period_frames"] = kick_period
            meta["kick_period_frames"] = ReviewMetricMeta(
                key="kick_period_frames",
                source_metric_keys=["summary.kick_periodicity.value.period_frames"],
                value=kick_period,
                unit="frame",
                availability=kick.availability if kick else "unavailable",
                confidence=kick.confidence if kick else 0.0,
                derivation="kick_periodicity.value.period_frames",
                reference_basis="frame_sequence",
            )

        # 可评估 / 峰检测：区分样本不足与无稳定周期峰
        required_min = 24  # MIN_PERIODICITY in lower_limb
        if sample_count < required_min:
            evaluable = 0
            peak_detected = None
        elif kick_details.get("reason") == "weak_or_no_peak" or kick_value is None:
            evaluable = 1
            peak_detected = 0
        else:
            evaluable = 1
            peak_detected = 1
        flat["kick_periodicity_evaluable"] = evaluable
        flat["kick_periodicity_peak_detected"] = peak_detected
        meta["kick_periodicity_evaluable"] = ReviewMetricMeta(
            key="kick_periodicity_evaluable",
            source_metric_keys=["summary.kick_periodicity"],
            value=evaluable,
            unit=None,
            availability="available" if evaluable else "unavailable",
            confidence=1.0 if evaluable else 0.0,
            derivation="sample_count >= MIN_PERIODICITY",
            reference_basis="frame_sequence",
        )
        meta["kick_periodicity_peak_detected"] = ReviewMetricMeta(
            key="kick_periodicity_peak_detected",
            source_metric_keys=["summary.kick_periodicity"],
            value=peak_detected,
            unit=None,
            availability="available" if peak_detected is not None else "unavailable",
            confidence=1.0 if peak_detected is not None else 0.0,
            derivation="detected peak in periodicity analysis",
            reference_basis="frame_sequence",
        )

        # ── 头部尖峰：计数 + 率 ──
        spike = _env(summary, "head_motion_spike_frames")
        spike_details = spike.details if spike else {}
        spike_count = spike_details.get("spike_count") if isinstance(spike_details, dict) else None
        if spike_count is not None:
            flat["head_motion_spike_count"] = spike_count
            meta["head_motion_spike_count"] = ReviewMetricMeta(
                key="head_motion_spike_count",
                source_metric_keys=["summary.head_motion_spike_frames.details.spike_count"],
                value=spike_count,
                unit="count",
                availability=spike.availability if spike else "unavailable",
                confidence=spike.confidence if spike else 0.0,
                derivation="head_motion_spike_frames.details.spike_count",
                reference_basis="frame_sequence",
            )
            if sample_count and spike.sample_count:
                rate = round(spike_count / max(spike.sample_count, 1), 3)
                flat["head_motion_spike_rate"] = rate
                meta["head_motion_spike_rate"] = ReviewMetricMeta(
                    key="head_motion_spike_rate",
                    source_metric_keys=["summary.head_motion_spike_frames.details.spike_count", "sample_count"],
                    value=rate,
                    unit="ratio",
                    availability=spike.availability if spike else "unavailable",
                    confidence=spike.confidence if spike else 0.0,
                    derivation="spike_count / sample_count",
                    reference_basis="frame_sequence",
                )

        # ── 像素波动经参考体长归一化（禁止固定像素阈值）──
        ref_val = ref.get("value_px") if isinstance(ref, dict) else None
        ref_avail = ref.get("availability") if isinstance(ref, dict) else "unavailable"
        ref_conf = ref.get("confidence") if isinstance(ref, dict) else 0.0

        hip_range_px = _scalar(_env(summary, "hip_vertical_range_px"))
        if hip_range_px is not None and ref_val not in (None, 0):
            ratio = round(hip_range_px / ref_val, 4)
            flat["hip_vertical_range_ratio"] = ratio
            meta["hip_vertical_range_ratio"] = ReviewMetricMeta(
                key="hip_vertical_range_ratio",
                source_metric_keys=[
                    "summary.hip_vertical_range_px",
                    "reference_body_length.value_px",
                ],
                value=ratio,
                unit="ratio",
                availability=_worst_availability(
                    [_env_availability(summary, "hip_vertical_range_px", "unavailable"), ref_avail]
                ),
                confidence=_min_confidence(
                    [_env_confidence(summary, "hip_vertical_range_px", 0.0), ref_conf]
                ),
                derivation="hip_vertical_range_px / reference_body_length",
                reference_basis="normalized_body_length",
            )

        head_range_px = _scalar(_env(summary, "head_vertical_range_px"))
        if head_range_px is not None and ref_val not in (None, 0):
            ratio = round(head_range_px / ref_val, 4)
            flat["head_vertical_range_ratio"] = ratio
            meta["head_vertical_range_ratio"] = ReviewMetricMeta(
                key="head_vertical_range_ratio",
                source_metric_keys=[
                    "summary.head_vertical_range_px",
                    "reference_body_length.value_px",
                ],
                value=ratio,
                unit="ratio",
                availability=_worst_availability(
                    [_env_availability(summary, "head_vertical_range_px", "unavailable"), ref_avail]
                ),
                confidence=_min_confidence(
                    [_env_confidence(summary, "head_vertical_range_px", 0.0), ref_conf]
                ),
                derivation="head_vertical_range_px / reference_body_length",
                reference_basis="normalized_body_length",
            )

        # ── 膝/肘 ROM（用于 evidence 展示，不作为触发键但保留 meta）──
        knee_rom = _env(summary, "knee_rom_deg")
        knee_details = knee_rom.details if knee_rom else {}
        for side in ("left", "right"):
            v = knee_details.get(side)
            if v is not None:
                key = f"knee_rom_{side}_deg"
                flat[key] = v
                meta[key] = ReviewMetricMeta(
                    key=key,
                    source_metric_keys=[f"summary.knee_rom_deg.details.{side}"],
                    value=v,
                    unit="deg",
                    availability=knee_rom.availability if knee_rom else "unavailable",
                    confidence=knee_rom.confidence if knee_rom else 0.0,
                    derivation=f"knee_rom_deg.details.{side}",
                    reference_basis="joint_geometry",
                )

        context = DiagnosticMetricsContext(
            metrics=flat,
            manual_tags=[],
            quality_summary={},
            metric_quality={},
            quality_decision={},
        )
        return ReviewAdapterResult(
            evaluation_context=context,
            metric_meta=meta,
            warnings=warnings,
        )

    @staticmethod
    def _add_scalar(
        summary: dict,
        key: str,
        flat: dict,
        meta: dict,
        unit: str | None,
    ) -> None:
        env = _env(summary, key)
        if env is None or env.value is None:
            return
        flat[key] = env.value
        meta[key] = ReviewMetricMeta(
            key=key,
            source_metric_keys=[f"summary.{key}"],
            value=env.value,
            unit=unit,
            availability=env.availability,
            confidence=env.confidence,
            derivation=None,
            reference_basis=env.reference_basis,
        )


def _env_availability(summary: dict, key: str, default: str) -> str:
    env = _env(summary, key)
    return env.availability if env else default


def _env_confidence(summary: dict, key: str, default: float) -> float:
    env = _env(summary, key)
    return env.confidence if env else default
