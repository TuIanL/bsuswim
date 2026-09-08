"""人工区间标注 ↔ 现有点事件 的双向 adapter。

核心原则（design D6 / tasks 4）：
* ``one authoritative input → derived representation``。派生结果 **MUST NOT** 写回
  任一侧；若需缓存，落独立 ``derived_*`` 表并带 ``source_signature``。
* ``segments → events``：人工区间为权威时，按 profile 映射派生
  ``hand_entry`` / ``catch_start`` / ``pull_end`` / ``hand_exit`` 点事件，供现有
  ``rhythm_metrics`` 使用。
* ``events → segments``：仅当四边界齐全时推导完整四阶段；缺 ``hand_exit`` 返回
  partial derivation 并标记 ``recovery_unavailable`` / ``missing_hand_exit``，
  **禁止按比例猜测分界点**。
* compatibility adapter 的 ``秒 → 帧`` 转换不反向定义新数据模型（design D3）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.services.reference_labels.profile import PhaseProfile

# 点事件名（与 side_technical_v1.yaml 的 event_sequences 对齐）
EVENT_HAND_ENTRY = "hand_entry"
EVENT_CATCH_START = "catch_start"
EVENT_PULL_END = "pull_end"
EVENT_HAND_EXIT = "hand_exit"


@dataclass
class DerivedEvent:
    name: str
    time_sec: float
    side: str
    cycle_id: str
    source: str = "manual_reference"
    labeled_by: str = "manual"
    revision_id: int | None = None


@dataclass
class SegmentDerivationResult:
    segments: list[dict] = field(default_factory=list)
    complete: bool = False
    missing_boundaries: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def time_sec_to_frame(time_sec: float, fps: float | None) -> int | None:
    """compatibility adapter：秒 → 帧。缺 frame_basis（fps）时返回 None 而非猜测。"""
    if fps is None or fps <= 0:
        return None
    return int(round(time_sec * float(fps)))


def segments_to_events(segments: list[Any], profile: PhaseProfile, revision_id: int | None = None) -> list[DerivedEvent]:
    """人工区间 → 点事件（供现有 rhythm/metrics 消费）。

    按 ``(side, cycle_id)`` 分组，取每个 phase 的相邻边界产出 4 个边界事件。
    """
    groups: dict[tuple[str, str], dict[str, dict]] = {}
    for seg in segments:
        if getattr(seg, "deleted_at", None) is not None:
            continue
        side = seg.side.value if hasattr(seg.side, "value") else seg.side
        code = seg.phase_code.value if hasattr(seg.phase_code, "value") else seg.phase_code
        groups.setdefault((side, seg.cycle_id), {})[code] = {
            "start": float(seg.start_time_sec),
            "end": float(seg.end_time_sec),
        }

    events: list[DerivedEvent] = []
    for (side, cycle_id), phases in groups.items():
        if "entry" not in phases:
            continue
        entry = phases["entry"]
        events.append(DerivedEvent(EVENT_HAND_ENTRY, entry["start"], side, cycle_id, revision_id=revision_id))
        if "catch" in phases:
            events.append(DerivedEvent(EVENT_CATCH_START, phases["catch"]["start"], side, cycle_id, revision_id=revision_id))
        if "push" in phases:
            events.append(DerivedEvent(EVENT_PULL_END, phases["push"]["start"], side, cycle_id, revision_id=revision_id))
            events.append(DerivedEvent(EVENT_HAND_EXIT, phases["push"]["end"], side, cycle_id, revision_id=revision_id))
    return events


def events_to_segments(events: list[dict], profile: PhaseProfile) -> SegmentDerivationResult:
    """点事件 → 人工区间。仅四边界齐全时生成完整四阶段。

    ``events`` 为 dict 列表，含 ``name`` / ``time_sec`` / ``side``。按 ``side`` 分区，
    按 ``hand_entry`` 切 cycle。缺 ``hand_exit`` 时返回 partial（entry/catch/push），
    标记 ``recovery_unavailable``；缺其它必选边界直接判缺。
    """
    by_side: dict[str, list[dict]] = {}
    for ev in events:
        by_side.setdefault(ev.get("side", "unknown"), []).append(ev)

    result = SegmentDerivationResult()
    required = [EVENT_HAND_ENTRY, EVENT_CATCH_START, EVENT_PULL_END, EVENT_HAND_EXIT]
    for side, evs in by_side.items():
        evs_sorted = sorted(evs, key=lambda e: e["time_sec"])
        # 按 hand_entry 边界切 cycle
        cycles: list[list[dict]] = []
        cur: list[dict] = []
        for e in evs_sorted:
            if e["name"] == EVENT_HAND_ENTRY and cur:
                cycles.append(cur)
                cur = []
            cur.append(e)
        if cur:
            cycles.append(cur)

        for ci, cyc in enumerate(cycles):
            # 末尾孤立的 hand_entry 只是下一周期的终止边界：仍参与为上一段 recovery
            # 提供结束时间，但 MUST NOT 被当作"缺边界的不完整周期"计入缺失。
            if len(cyc) == 1 and cyc[0]["name"] == EVENT_HAND_ENTRY:
                continue
            by_name = {e["name"]: e for e in cyc}
            missing = [b for b in required if b not in by_name]
            if missing:
                result.missing_boundaries.extend(missing)
                if EVENT_HAND_EXIT in missing:
                    result.notes.append(f"side={side} cycle#{ci}: recovery_unavailable（缺 hand_exit，禁止猜测）")
                continue
            cycle_label = f"{side}-{ci}"
            result.segments.append(_mk_segment("entry", by_name[EVENT_HAND_ENTRY]["time_sec"], by_name[EVENT_CATCH_START]["time_sec"], side, cycle_label, "event_derived"))
            result.segments.append(_mk_segment("catch", by_name[EVENT_CATCH_START]["time_sec"], by_name[EVENT_PULL_END]["time_sec"], side, cycle_label, "event_derived"))
            result.segments.append(_mk_segment("push", by_name[EVENT_PULL_END]["time_sec"], by_name[EVENT_HAND_EXIT]["time_sec"], side, cycle_label, "event_derived"))
            # recovery 收尾于下一同侧 hand_entry（若有）
            next_hand_entry = None
            if ci + 1 < len(cycles):
                nhe = next((e for e in cycles[ci + 1] if e["name"] == EVENT_HAND_ENTRY), None)
                next_hand_entry = nhe["time_sec"] if nhe else None
            if next_hand_entry is not None:
                result.segments.append(_mk_segment("recovery", by_name[EVENT_HAND_EXIT]["time_sec"], next_hand_entry, side, cycle_label, "event_derived"))
    result.complete = not result.missing_boundaries
    return result


def _mk_segment(phase_code: str, start: float, end: float, side: str, cycle_id: str, derivation: str) -> dict:
    return {
        "phase_code": phase_code,
        "start_time_sec": start,
        "end_time_sec": end,
        "side": side,
        "cycle_id": cycle_id,
        "derivation": derivation,
    }


def detect_conflicts(
    derived_events: list[DerivedEvent], source_events: list[dict], tolerance_sec: float = 0.05
) -> list[dict]:
    """人工派生事件与现有点事件交叉检测冲突（不自动修复、不回写）。

    同一 ``(side, name)`` 下时间偏差 > 容差即报 conflict/warning。
    """
    warnings: list[dict] = []
    src = {(e.get("side"), e.get("name")): e["time_sec"] for e in source_events}
    for de in derived_events:
        key = (de.side, de.name)
        if key in src:
            dev = abs(de.time_sec - src[key])
            if dev > tolerance_sec:
                warnings.append(
                    {
                        "type": "event_time_deviation",
                        "side": de.side,
                        "event": de.name,
                        "manual_time_sec": de.time_sec,
                        "source_time_sec": src[key],
                        "deviation_sec": round(dev, 4),
                    }
                )
    return warnings
