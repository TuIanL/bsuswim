import hashlib
from pathlib import Path

import yaml

from app.core.config import get_settings
from app.schemas.report_interpretation import InterpretationInput, KnowledgeEntry
from .projector import stable_json


KNOWLEDGE_PATH = Path(__file__).with_name("knowledge") / "swimming_v1.yaml"
KNOWLEDGE_V2_PATH = Path(__file__).with_name("knowledge") / "swimming_kb_v2.yaml"

# 指标别名：知识库作者使用的规范名 → 系统实际指标 key。
# 检索时把一个知识条目声明的指标展开为其别名集合，与实际事实 source_key 做并集匹配，
# 避免因改名（如 elbow_angle_deg → left/right_elbow_angle_deg）导致静默漏检。
METRIC_ALIASES: dict[str, tuple[str, ...]] = {
    "elbow_angle_deg": ("left_elbow_angle_deg", "right_elbow_angle_deg"),
    "knee_angle_deg": ("left_knee_angle_deg", "right_knee_angle_deg"),
    "head_torso_sync": ("head_body_synchrony",),
    "wrist_trajectory": ("normalized_wrist_trajectory",),
    "left_right_difference": ("left_right_kick_timing",),
    "asymmetry_index": ("left_right_kick_timing",),
}

# 机位归一化：知识库视角值 → 系统视角值（五页报告 view_type 用 "side"）。
# 空元组表示"不限定机位"（any / none / multi_view）。
VIEW_ALIASES: dict[str, tuple[str, ...]] = {
    "side_2d": ("side",),
    "front": ("front",),
    "underwater": ("underwater",),
    "any": (),
    "none": (),
    "multi_view": (),
}

# 可作为训练建议依据的证据等级；governance / low 只用于语言约束，不作为训练依据。
TRAINING_EVIDENCE_LEVELS = {"high", "moderate", "moderate_to_high"}


def _default_knowledge_path() -> Path:
    source = get_settings().ai_interpretation_knowledge_source
    if source == "v1":
        return KNOWLEDGE_PATH
    return KNOWLEDGE_V2_PATH


def _expand_metric_keys(metric_keys: list[str]) -> set[str]:
    expanded: set[str] = set()
    for key in metric_keys:
        expanded.add(key)
        for target in METRIC_ALIASES.get(key, ()):
            expanded.add(target)
    return expanded


class KnowledgeRegistry:
    def __init__(self, path: Path | None = None):
        self.path = path or _default_knowledge_path()
        payload = yaml.safe_load(self.path.read_text(encoding="utf-8")) or {}
        self.entries = [KnowledgeEntry.model_validate(item) for item in payload.get("entries", [])]
        self.active_entries = [entry for entry in self.entries if entry.review_status == "active"]
        version_payload = [entry.model_dump(mode="json") for entry in self.active_entries]
        self.version = hashlib.sha256(stable_json(version_payload).encode("utf-8")).hexdigest()

    def retrieve(self, interpretation_input: InterpretationInput, limit: int = 6) -> list[KnowledgeEntry]:
        metric_keys = {fact.source_key for fact in interpretation_input.facts if fact.kind == "metric"}
        finding_codes = {fact.source_key for fact in interpretation_input.facts if fact.kind == "finding"}
        stroke = interpretation_input.context.stroke_type
        level = interpretation_input.context.athlete_level
        view = interpretation_input.context.view_type
        if view in ("side_2d", "side"):
            view = "side"
        ranked: list[tuple[int, str, KnowledgeEntry]] = []
        for entry in self.active_entries:
            # 泳姿 / 机位 / 水平硬过滤：不匹配即排除，不打分。
            if entry.stroke_types and stroke and stroke not in entry.stroke_types:
                continue
            if entry.view_types and view and view not in entry.view_types:
                continue
            if entry.athlete_levels and level and level not in entry.athlete_levels:
                continue
            expanded_metrics = _expand_metric_keys(entry.metric_keys)
            score = 0
            score += 5 * len(metric_keys.intersection(expanded_metrics))
            score += 7 * len(finding_codes.intersection(entry.finding_codes))
            if stroke and stroke in entry.stroke_types:
                score += 2
            if level and level in entry.athlete_levels:
                score += 1
            if score:
                ranked.append((score, entry.knowledge_id, entry))
        ranked.sort(key=lambda item: (-item[0], item[1]))
        return [item[2] for item in ranked[:limit]]
