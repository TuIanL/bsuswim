"""Stability display-index computation.

Reads the versioned YAML config and produces 0-100 display values per axis.
These are within-clip visualization indices only, NOT validated technical scores.
Inputs that are missing produce availability=unavailable (rendered as N/A).
"""

import hashlib
import json
from functools import lru_cache
from pathlib import Path

import yaml

CONFIG_DIR = Path(__file__).parent / "config"
CONFIG_PATH = CONFIG_DIR / "stability_display_index_v1.yaml"


def config_hash() -> str:
    return hashlib.sha256(CONFIG_PATH.read_bytes()).hexdigest()


@lru_cache(maxsize=1)
def _load_config() -> dict:
    return yaml.safe_load(CONFIG_PATH.read_text())


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


def _weighted_score(axis_cfg: dict, inputs: dict) -> tuple[float | None, dict]:
    """Return (display_value 0-100 or None, per-input detail)."""
    available_items = []
    total_weight = 0.0
    detail: dict = {}
    for name, spec in axis_cfg.get("inputs", {}).items():
        raw = inputs.get(name)
        if raw is None:
            detail[name] = {"raw": None, "used": False}
            continue
        direction = spec.get("direction", "higher_is_more_stable")
        lo, hi = spec.get("min", 0.0), spec.get("max", 1.0)
        soft_cap = spec.get("soft_cap")
        if direction == "higher_is_more_stable":
            norm = _clamp(raw, lo, hi)
            scaled = (norm - lo) / (hi - lo) * 100.0 if hi > lo else 100.0
        else:  # lower_is_more_stable
            capped = soft_cap if soft_cap is not None else hi
            norm = _clamp(raw, lo, capped)
            scaled = (1.0 - (norm - lo) / (capped - lo)) * 100.0 if capped > lo else 100.0
        detail[name] = {"raw": raw, "scaled": round(scaled, 2), "used": True}
        available_items.append((spec.get("weight", 1.0), scaled))
        total_weight += spec.get("weight", 1.0)

    min_inputs = axis_cfg.get("minimum_available_inputs", 1)
    if len(available_items) < min_inputs:
        return None, detail
    if total_weight == 0:
        return None, detail
    score = sum(w * s for w, s in available_items) / total_weight
    return round(score, 1), detail


def compute_axes(raw_inputs: dict) -> list[dict]:
    """raw_inputs: axis_name -> {input_name: value}. Returns list of axis dicts."""
    cfg = _load_config()
    axes_out = []
    for axis_name, axis_cfg in cfg["axes"].items():
        inputs = raw_inputs.get(axis_name, {})
        score, detail = _weighted_score(axis_cfg, inputs)
        availability = "available" if score is not None else "unavailable"
        axes_out.append(
            {
                "axis": axis_name,
                "display_value": score,
                "availability": availability,
                "source_raw_values": detail,
                "formula_id": f"stability-display-index.v1.{axis_name}",
            }
        )
    return axes_out


def available_axis_count(axes: list[dict]) -> int:
    return sum(1 for a in axes if a["availability"] in ("available", "degraded"))


def config_signature_inputs() -> dict:
    return {
        "style_profile_hash": "unused",  # filled by caller
        "stability_index_config_hash": config_hash(),
    }
