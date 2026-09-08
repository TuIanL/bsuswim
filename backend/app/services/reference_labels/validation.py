"""分级校验（L1 结构 / L2 周期完整性 / L3 profile 严格）与不可变守卫。

设计要点（design D7 + tasks 3）：
* DB 层不建 exclusion constraint；全部在应用层按状态逐级收紧。
* 重叠约束的作用域是 ``(side, cycle_id)``，**不是全局**——左右臂在全局时间轴上
  重叠是自由泳正常交替划臂，MUST NOT 报错。
* ``side`` 收敛：``reviewed`` / ``frozen`` 数据只允许 ``left`` / ``right``，
  ``both`` / ``unknown`` 仅允许 ``draft``，进入发布态 MUST 被拦截。
* revision 离开 ``draft``（含 ``in_review``）内容永久锁定；修改 MUST 经 fork。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.models.manual_reference_label import (
    ManualAnnotationRevision,
    ManualRevisionStatus,
    SegmentSide,
)
from app.services.reference_labels.errors import EditVersionConflictError, RevisionImmutableError
from app.services.reference_labels.profile import PhaseProfile

_GAP_THRESHOLD_SEC = 0.05  # 相邻 phase 空隙阈值（50ms）


@dataclass
class ValidationError:
    level: str  # L1 / L2 / L3
    code: str
    message: str
    side: str | None = None
    cycle_id: str | None = None
    phase_code: str | None = None
    segment_ids: list[int] = field(default_factory=list)


@dataclass
class ValidationResult:
    errors: list[ValidationError] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    @property
    def l1_errors(self) -> list[ValidationError]:
        return [e for e in self.errors if e.level == "L1"]

    @property
    def l2_errors(self) -> list[ValidationError]:
        return [e for e in self.errors if e.level == "L2"]

    @property
    def l3_errors(self) -> list[ValidationError]:
        return [e for e in self.errors if e.level == "L3"]


def _seg_view(seg: Any) -> dict:
    if isinstance(seg, dict):
        return seg
    return {
        "id": getattr(seg, "id", None),
        "cycle_id": seg.cycle_id,
        "side": seg.side.value if isinstance(seg.side, SegmentSide) else seg.side,
        "phase_code": seg.phase_code.value if hasattr(seg.phase_code, "value") else seg.phase_code,
        "start_time_sec": float(seg.start_time_sec),
        "end_time_sec": float(seg.end_time_sec),
        "deleted_at": getattr(seg, "deleted_at", None),
    }


# ── L1 结构校验 ──


def validate_l1(segments: list[Any], duration_sec: float | None, profile: PhaseProfile) -> list[ValidationError]:
    errors: list[ValidationError] = []
    allowed_phases = {p.code for p in profile.phases}
    allowed_sides = {s.value for s in SegmentSide}
    for seg in segments:
        v = _seg_view(seg)
        if v.get("deleted_at") is not None:
            continue
        side, code = v["side"], v["phase_code"]
        if side not in allowed_sides:
            errors.append(ValidationError("L1", "INVALID_SIDE", f"side 不在枚举内: {side}", side=side))
        if code not in allowed_phases:
            errors.append(
                ValidationError("L1", "INVALID_PHASE_CODE", f"phase_code 不属于 profile: {code}", side=side, phase_code=code)
            )
        if not v.get("cycle_id"):
            errors.append(ValidationError("L1", "MISSING_CYCLE_ID", "cycle_id 为空", side=side, phase_code=code))
        start, end = v["start_time_sec"], v["end_time_sec"]
        if start < 0:
            errors.append(ValidationError("L1", "NEGATIVE_START", f"start_time_sec < 0: {start}", side=side, phase_code=code))
        if end <= start:
            errors.append(
                ValidationError("L1", "INVERTED_INTERVAL", f"end <= start: {start}~{end}", side=side, phase_code=code)
            )
        if duration_sec is not None and end > duration_sec + 1e-6:
            errors.append(
                ValidationError(
                    "L1", "EXCEEDS_DURATION", f"end {end} 超出视频时长 {duration_sec}", side=side, phase_code=code
                )
            )
    return errors


# ── L2 周期完整性校验 ──


def validate_l2(segments: list[Any], side_converge: bool) -> list[ValidationError]:
    errors: list[ValidationError] = []
    groups: dict[tuple[str, str], list[dict]] = {}
    for seg in segments:
        v = _seg_view(seg)
        if v.get("deleted_at") is not None:
            continue
        groups.setdefault((v["side"], v["cycle_id"]), []).append(v)

    for (side, cycle_id), segs in groups.items():
        if side_converge and side not in (SegmentSide.LEFT.value, SegmentSide.RIGHT.value):
            for s in segs:
                errors.append(
                    ValidationError(
                        "L2", "SIDE_NOT_CONVERGED", f"发布态不允许 side={side}", side=side, cycle_id=cycle_id,
                        segment_ids=[s.get("id")] if s.get("id") else [],
                    )
                )
        # 按 start 排序，检查齐全 / 重叠 / 空隙
        ordered = sorted(segs, key=lambda x: x["start_time_sec"])
        seen_phases = set()
        for s in ordered:
            if s["phase_code"] in seen_phases:
                errors.append(
                    ValidationError(
                        "L2", "PHASE_DUPLICATE", f"同 (side,cycle) 内 phase 重复: {s['phase_code']}",
                        side=side, cycle_id=cycle_id, phase_code=s["phase_code"],
                        segment_ids=[s.get("id")] if s.get("id") else [],
                    )
                )
            seen_phases.add(s["phase_code"])
        for prev, nxt in zip(ordered, ordered[1:]):
            if nxt["start_time_sec"] < prev["end_time_sec"] - 1e-6:
                errors.append(
                    ValidationError(
                        "L2", "OVERLAP", f"同 (side,cycle) 内区间重叠: {prev['phase_code']} 与 {nxt['phase_code']}",
                        side=side, cycle_id=cycle_id,
                        segment_ids=[i for i in (prev.get("id"), nxt.get("id")) if i],
                    )
                )
            gap = nxt["start_time_sec"] - prev["end_time_sec"]
            if gap > _GAP_THRESHOLD_SEC:
                errors.append(
                    ValidationError(
                        "L2", "GAP_TOO_LARGE", f"相邻 phase 空隙 {gap:.3f}s > 阈值 {_GAP_THRESHOLD_SEC}s",
                        side=side, cycle_id=cycle_id,
                        phase_code=nxt["phase_code"],
                        segment_ids=[i for i in (prev.get("id"), nxt.get("id")) if i],
                    )
                )
    return errors


# ── L3 profile 严格校验 ──


def validate_l3(segments: list[Any], profile: PhaseProfile, minimum_complete_cycles: int = 2) -> list[ValidationError]:
    errors: list[ValidationError] = []
    groups: dict[tuple[str, str], list[dict]] = {}
    for seg in segments:
        v = _seg_view(seg)
        if v.get("deleted_at") is not None:
            continue
        groups.setdefault((v["side"], v["cycle_id"]), []).append(v)

    complete_cycles = 0
    required = {p.code for p in profile.phases}
    for (side, cycle_id), segs in groups.items():
        present = {s["phase_code"] for s in segs}
        if present >= required:
            complete_cycles += 1
        else:
            missing = required - present
            errors.append(
                ValidationError(
                    "L3", "INCOMPLETE_CYCLE", f"完整 cycle 缺 phase: {sorted(missing)}", side=side, cycle_id=cycle_id
                )
            )
    if complete_cycles < minimum_complete_cycles:
        errors.append(
            ValidationError(
                "L3", "TOO_FEW_COMPLETE_CYCLES",
                f"完整 cycle 数 {complete_cycles} < 要求 {minimum_complete_cycles}",
            )
        )
    return errors


# ── 组合入口 ──


def run_validation(
    segments: list[Any],
    profile: PhaseProfile,
    target_status: ManualRevisionStatus,
    *,
    duration_sec: float | None = None,
    minimum_complete_cycles: int = 2,
) -> ValidationResult:
    """按目标状态逐级跑校验。

    * ``draft``：仅 L1（宽松，允许编辑）
    * ``in_review`` / ``reviewed`` / ``rejected``：L1 + L2 + side 收敛
    * ``frozen``：L1 + L2 + side 收敛 + L3
    """
    errors: list[ValidationError] = []
    errors += validate_l1(segments, duration_sec, profile)
    if target_status is not ManualRevisionStatus.DRAFT:
        side_converge = target_status in (
            ManualRevisionStatus.IN_REVIEW,
            ManualRevisionStatus.REVIEWED,
            ManualRevisionStatus.FROZEN,
        )
        errors += validate_l2(segments, side_converge=side_converge)
        if target_status is ManualRevisionStatus.FROZEN:
            errors += validate_l3(segments, profile, minimum_complete_cycles=minimum_complete_cycles)
    return ValidationResult(errors=errors)


# ── 不可变守卫 + 乐观锁 ──


def assert_revision_mutable(revision: ManualAnnotationRevision, expected_edit_version: int | None = None) -> None:
    """revision 离开 draft 后任何写操作 MUST 被拒绝；in_review 即锁内容。

    乐观锁：传入 ``expected_edit_version`` 且与当前不一致时抛
    ``EditVersionConflictError``（409），不静默覆盖。
    """
    if not revision.status.is_mutable:
        raise RevisionImmutableError(
            f"revision {revision.id} 状态为 {revision.status.value}，内容已锁定，修改需 fork 新 draft"
        )
    if expected_edit_version is not None and expected_edit_version != revision.edit_version:
        raise EditVersionConflictError(
            f"edit_version 不匹配：期望 {expected_edit_version}，当前 {revision.edit_version}"
        )
