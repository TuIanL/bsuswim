"""Phase profile（环节定义）加载与校验。

profile 是「人工区间标注 ↔ 现有点事件」共享的唯一动作定义来源。loader 负责：
* 按 ``phase_profile_id`` 从 YAML 加载；
* 校验结构完整性（含 ``boundary_definitions`` 必填，且每条均有
  ``operational_definition``）；
* 计算稳定的 ``phase_profile_hash``（canonical JSON → sha256）。
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import yaml

_PROFILES_DIR = os.path.join(os.path.dirname(__file__), "profiles")

_REQUIRED_BOUNDARY_KEYS = ("display", "operational_definition", "reference_joint", "annotation_guidance")


class PhaseProfileError(ValueError):
    """profile 结构不合法。"""


@dataclass(frozen=True)
class PhaseDef:
    code: str
    display: str
    start: str
    end: str


@dataclass(frozen=True)
class BoundaryDef:
    name: str
    display: str
    operational_definition: str
    reference_joint: str
    annotation_guidance: str


@dataclass(frozen=True)
class PhaseProfile:
    id: str
    version: str
    cycle_partition_by: str
    cycle_boundary: str
    phases: tuple[PhaseDef, ...]
    required_boundaries: tuple[str, ...]
    optional_boundaries: tuple[str, ...]
    boundary_definitions: dict[str, BoundaryDef]
    profile_hash: str

    @property
    def phase_display_map(self) -> dict[str, str]:
        return {p.code: p.display for p in self.phases}

    @property
    def phase_code_map(self) -> dict[str, str]:
        return {p.display: p.code for p in self.phases}


def _canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def compute_profile_hash(data: dict) -> str:
    """对 profile 内容计算稳定 hash（排除自身 hash 字段）。"""
    payload = {k: v for k, v in data.items() if k != "profile_hash"}
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _load_raw(profile_id: str) -> dict:
    for ext in (".yaml", ".yml"):
        path = os.path.join(_PROFILES_DIR, f"{profile_id}{ext}")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
    raise PhaseProfileError(f"Phase profile '{profile_id}' not found")


def _validate(data: dict) -> None:
    missing = [k for k in ("id", "version", "cycle_definition", "phases") if k not in data]
    if missing:
        raise PhaseProfileError(f"Phase profile 缺字段: {missing}")

    phases = data["phases"]
    if not isinstance(phases, list) or not phases:
        raise PhaseProfileError("phases 必须为非空列表")

    codes = set()
    for ph in phases:
        for key in ("code", "display", "start", "end"):
            if key not in ph:
                raise PhaseProfileError(f"phase 缺字段 {key}: {ph}")
        if ph["code"] in codes:
            raise PhaseProfileError(f"phase code 重复: {ph['code']}")
        codes.add(ph["code"])

    bd = data.get("boundary_definitions")
    if not isinstance(bd, dict) or not bd:
        raise PhaseProfileError("boundary_definitions 为必填且不得为空")
    for name, spec in bd.items():
        missing_keys = [k for k in _REQUIRED_BOUNDARY_KEYS if not spec.get(k)]
        if missing_keys:
            raise PhaseProfileError(
                f"boundary '{name}' 缺必填项: {missing_keys}（operational definition 为人工标注一致性所必需）"
            )

    rb = data.get("required_boundaries", [])
    for b in rb:
        if b not in bd:
            raise PhaseProfileError(f"required_boundary '{b}' 未在 boundary_definitions 中定义")


def _build(data: dict) -> PhaseProfile:
    _validate(data)
    cd = data["cycle_definition"]
    phases = tuple(
        PhaseDef(code=p["code"], display=p["display"], start=p["start"], end=p["end"]) for p in data["phases"]
    )
    boundary_definitions = {
        name: BoundaryDef(
            name=name,
            display=spec.get("display", name),
            operational_definition=spec["operational_definition"],
            reference_joint=spec["reference_joint"],
            annotation_guidance=spec["annotation_guidance"],
        )
        for name, spec in data["boundary_definitions"].items()
    }
    return PhaseProfile(
        id=data["id"],
        version=str(data["version"]),
        cycle_partition_by=cd.get("partition_by", "side"),
        cycle_boundary=cd.get("boundary", "hand_entry"),
        phases=phases,
        required_boundaries=tuple(data.get("required_boundaries", [])),
        optional_boundaries=tuple(data.get("optional_boundaries", [])),
        boundary_definitions=boundary_definitions,
        profile_hash=compute_profile_hash(data),
    )


@lru_cache(maxsize=32)
def get_phase_profile(profile_id: str) -> PhaseProfile:
    """加载并校验 profile（带缓存）。未知 profile 抛 ``PhaseProfileError``。"""
    return _build(_load_raw(profile_id))
