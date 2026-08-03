"""将外部 swim_knowledge_base_v1.jsonl 转换为系统格式知识文件。

对齐动作：
- 字段名映射到 KnowledgeEntry schema（含扩展元数据字段）
- 泳姿/机位归一化（all→不限定，side_2d→side）
- 指标别名在检索期解析（此处保留 KB 原始指标名，metric_keys 不改写）
- 适用性标注：当前 2D 运动学管线无对应指标的知识卡 → inactive
- 来源记录透传 source_records

用法：
  python backend/scripts/convert_swimming_kb_v1.py \
    --input /path/to/swim_knowledge_base_v1/swimming_knowledge_base_v1.jsonl \
    --output backend/app/services/report_interpretation/knowledge/swimming_kb_v2.yaml
"""

import argparse
import json
from pathlib import Path

import yaml

# 当前 side_2d_kinematics_5page 管线真实指标集（含投影层派生的 *_norm 归一化指标）。
SYSTEM_METRIC_KEYS = {
    "ankle_vertical_range_px", "arm_extension_ratio", "body_angle_std_deg",
    "body_axis_angle_deg", "elbow_rom_deg", "head_body_synchrony",
    "head_motion_spike_frames", "head_shoulder_relative_offset",
    "head_vertical_range_px", "hip_vertical_range_px", "kick_periodicity",
    "knee_rom_deg", "left_elbow_angle_deg", "left_knee_angle_deg",
    "left_right_kick_timing", "normalized_wrist_trajectory", "posture_stability_cv",
    "right_elbow_angle_deg", "right_knee_angle_deg", "shoulder_vertical_range_px",
    "technical_stability_score", "torso_axis_angle_deg", "trunk_vertical_stability",
    "wrist_velocity_px_per_frame",
    "ankle_vertical_range_norm", "head_vertical_range_norm",
    "hip_vertical_range_norm", "shoulder_vertical_range_norm",
}

# 与 knowledge.py 保持一致：KB 规范名 → 系统指标 key。
METRIC_ALIASES = {
    "elbow_angle_deg": ("left_elbow_angle_deg", "right_elbow_angle_deg"),
    "knee_angle_deg": ("left_knee_angle_deg", "right_knee_angle_deg"),
    "head_torso_sync": ("head_body_synchrony",),
    "wrist_trajectory": ("normalized_wrist_trajectory",),
    "left_right_difference": ("left_right_kick_timing",),
    "asymmetry_index": ("left_right_kick_timing",),
}

VIEW_MAP = {
    "side_2d": ["side"],
    "front": ["front"],
    "underwater": ["underwater"],
    "any": [],
    "none": [],
    "multi_view": [],
}

STROKE_MAP = {"all": [], "freestyle": ["freestyle"]}


def _normalize_list(value, mapping):
    out = []
    for item in value or []:
        normalized = mapping.get(item)
        if normalized is None:
            out.append(item)
        else:
            out.extend(normalized)
    return sorted(set(out))


def _is_applicable(metrics: list[str]) -> bool:
    """当前管线是否可能触发该知识卡：指标集与系统指标有交集，或为全局治理卡。"""
    if "all" in metrics or "all_2d" in metrics:
        return True
    expanded = set()
    for metric in metrics:
        expanded.add(metric)
        expanded.update(METRIC_ALIASES.get(metric, ()))
    return bool(expanded & SYSTEM_METRIC_KEYS)


def convert_card(card: dict) -> dict:
    knowledge_id = str(card["id"])
    source_records = card.get("source_records") or []
    source_titles = ", ".join(item.get("title", "") for item in source_records[:3])
    applicable = _is_applicable(card.get("metrics") or [])
    return {
        "knowledge_id": knowledge_id,
        "version": "1.0",
        "title": str(card.get("title", "")),
        "summary": str(card.get("core", "")),
        "stroke_types": _normalize_list(card.get("stroke"), STROKE_MAP),
        "metric_keys": sorted(set(card.get("metrics") or [])),
        "finding_codes": [],
        "athlete_levels": [],
        "training_goals": [],
        "contraindications": [],
        "source_title": f"游泳表现分析知识库 v1：{source_titles}",
        "source_locator": f"swim_knowledge_base_v1#{knowledge_id}",
        "review_status": "active" if applicable else "inactive",
        "reviewed_by": "swim-knowledge-base-v1-authors",
        "reviewed_at": "2026-07-31",
        "domain": card.get("domain"),
        "view_types": _normalize_list(card.get("view"), VIEW_MAP),
        "distance_contexts": [],
        "evidence_level": str(card.get("evidence", "moderate")),
        "forbidden": list(card.get("forbidden") or []),
        "coach_text": card.get("coach_text"),
        "actions": list(card.get("actions") or []),
        "audience": ["coach", "athlete"],
        "applicable_pipelines": ["side_2d_kinematics_5page"] if applicable else [],
        "interpretations": list(card.get("interpretation") or []),
        "alternatives": list(card.get("alternatives") or []),
        "required_evidence": list(card.get("required") or []),
        "source_records": source_records,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    cards = []
    with args.input.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            cards.append(convert_card(json.loads(line)))

    active = sum(1 for card in cards if card["review_status"] == "active")
    payload = {
        "schema_version": "swim-knowledge.v2",
        "source": str(args.input),
        "entries": cards,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        yaml.safe_dump(payload, allow_unicode=True, sort_keys=False, width=100),
        encoding="utf-8",
    )
    print(f"converted {len(cards)} cards -> {args.output} ({active} active, {len(cards) - active} inactive)")


if __name__ == "__main__":
    main()
