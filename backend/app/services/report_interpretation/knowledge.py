import hashlib
from pathlib import Path

import yaml

from app.schemas.report_interpretation import InterpretationInput, KnowledgeEntry
from .projector import stable_json


KNOWLEDGE_PATH = Path(__file__).with_name("knowledge") / "swimming_v1.yaml"


class KnowledgeRegistry:
    def __init__(self, path: Path = KNOWLEDGE_PATH):
        self.path = path
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        self.entries = [KnowledgeEntry.model_validate(item) for item in payload.get("entries", [])]
        self.active_entries = [entry for entry in self.entries if entry.review_status == "active"]
        version_payload = [entry.model_dump(mode="json") for entry in self.active_entries]
        self.version = hashlib.sha256(stable_json(version_payload).encode("utf-8")).hexdigest()

    def retrieve(self, interpretation_input: InterpretationInput, limit: int = 6) -> list[KnowledgeEntry]:
        metric_keys = {fact.source_key for fact in interpretation_input.facts if fact.kind == "metric"}
        finding_codes = {fact.source_key for fact in interpretation_input.facts if fact.kind == "finding"}
        stroke = interpretation_input.context.stroke_type
        level = interpretation_input.context.athlete_level
        ranked: list[tuple[int, str, KnowledgeEntry]] = []
        for entry in self.active_entries:
            if entry.stroke_types and stroke and stroke not in entry.stroke_types:
                continue
            if entry.athlete_levels and level and level not in entry.athlete_levels:
                continue
            score = 0
            score += 5 * len(metric_keys.intersection(entry.metric_keys))
            score += 7 * len(finding_codes.intersection(entry.finding_codes))
            if stroke and stroke in entry.stroke_types:
                score += 2
            if level and level in entry.athlete_levels:
                score += 1
            if score:
                ranked.append((score, entry.knowledge_id, entry))
        ranked.sort(key=lambda item: (-item[0], item[1]))
        return [item[2] for item in ranked[:limit]]
