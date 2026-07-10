"""Profile provider 抽象与 YAML 实现。"""

from typing import Any, Protocol

import yaml
from pydantic import BaseModel, Field

from app.services.annotation_quality.models import QualityProfileRef


class ModuleProfile(BaseModel):
    core: bool = False
    required_landmarks: list[str] = Field(default_factory=list)
    required_events: list[str] = Field(default_factory=list)
    required_references: list[str] = Field(default_factory=list)
    minimum_landmark_coverage: float = 0.80
    minimum_sample_frames: int = 3
    minimum_event_count: int = 1
    minimum_complete_cycles: int = 2


class GlobalGate(BaseModel):
    minimum_ready_core_modules: int = 2


class QualityProfile(BaseModel):
    id: str
    version: str
    global_gate: GlobalGate = Field(default_factory=GlobalGate)
    modules: dict[str, ModuleProfile] = Field(default_factory=dict)
    event_sequences: dict[str, Any] = Field(default_factory=dict)


class QualityProfileProvider(Protocol):
    def get(self, profile_id: str) -> QualityProfile: ...


class YamlQualityProfileProvider:
    def __init__(self, profiles_dir: str):
        self.profiles_dir = profiles_dir

    def get(self, profile_id: str) -> QualityProfile:
        import os
        path = os.path.join(self.profiles_dir, f"{profile_id}.yaml")
        if not os.path.exists(path):
            path = os.path.join(self.profiles_dir, f"{profile_id}.yml")
        if not os.path.exists(path):
            raise ValueError(f"Profile {profile_id} not found")
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return QualityProfile(**data)
