"""segment 内容哈希（content_hash）规范化。

规则（来自 design D2b + tasks 3.5）：

* 仅对语义字段参与哈希，排除一切非语义字段（id / 时间戳 / revision_id /
  cycle_index / provenance 等）。
* 语义字段：``cycle_id`` / ``side`` / ``phase_code`` / ``start_time_sec`` /
  ``end_time_sec`` / ``confidence`` / ``note``。
* 浮点时间按固定小数位（4 位）序列化，避免 0.1+0.2 类浮点表示差异导致同内容
  不同 hash。
* 已 soft delete（``deleted_at`` 非空）的 segment 不参与。
* 多条 segment 按 ``(cycle_id, side, phase_code)`` 字典序排序后整体哈希，
  保证"相同内容两次计算结果相等"。

``content_hash`` 的语义：证明内容身份、检测是否变化、保证分析/ML 导出可复现。
它不是去重键——fork 出来的 revision 内容可与源完全相同（见 design D2b）。
"""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from typing import Any

# 参与哈希的语义字段（顺序即此列表，键名稳定）
_SEMANTIC_FIELDS = ("cycle_id", "side", "phase_code", "start_time_sec", "end_time_sec", "confidence", "note")


def _fmt_value(value: Any) -> Any:
    """规范化字段值。

    ``Numeric`` 列经 SQLAlchemy 读回是 ``Decimal``，不是 ``float``，因此 MUST 显式
    纳入数值分支，否则 json.dumps 会抛 "Object of type Decimal is not JSON serializable"。
    """
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float, Decimal)):
        return f"{value:.4f}"
    return value


def segment_semantic_fields(seg: dict) -> dict:
    """从 segment 行（ORM 或 dict）提取语义字段，浮点时间固定 4 位小数。"""
    out: dict[str, Any] = {}
    for key in _SEMANTIC_FIELDS:
        raw = seg.get(key) if isinstance(seg, dict) else getattr(seg, key, None)
        out[key] = _fmt_value(raw)
    return out


def _is_deleted(seg: Any) -> bool:
    if isinstance(seg, dict):
        return seg.get("deleted_at") is not None
    return getattr(seg, "deleted_at", None) is not None


def compute_segments_hash(segments: list[Any]) -> str:
    """对（非 soft-delete 的）segment 列表计算稳定 sha256。

    ``segments`` 元素可为 ORM ``ManualPhaseSegment`` 或 dict（含语义字段与
    可选 ``deleted_at``）。
    """
    records = []
    for seg in segments:
        if _is_deleted(seg):
            continue
        fields = segment_semantic_fields(seg)
        records.append(
            (
                fields["cycle_id"],
                fields["side"],
                fields["phase_code"],
                fields["start_time_sec"],
                fields["end_time_sec"],
                fields["confidence"],
                fields["note"],
            )
        )
    records.sort(key=lambda r: (r[0], r[1], r[2]))
    canonical = json.dumps(records, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
