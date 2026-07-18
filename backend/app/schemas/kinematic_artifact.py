"""Pydantic schemas for kinematic visual artifacts (API layer)."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from app.services.kinematic_artifacts.constants import (
    ARTIFACT_KEYS,
    ArtifactSetStatus,
    ArtifactStatus,
    ArtifactType,
    SCHEMA_VERSION,
    STYLE_PROFILE,
    GENERATOR_NAME,
    GENERATOR_VERSION,
)


class ArtifactPresentation(BaseModel):
    title: str | None = None
    label: str | None = None
    value: str | None = None
    caption: str | None = None
    report_asset_type: str | None = None  # annotated_frame | image


class SourceMetricRef(BaseModel):
    schema_version: str
    calculator: str
    calculator_version: str
    hash: str


class GeneratorRef(BaseModel):
    name: str = GENERATOR_NAME
    version: str = GENERATOR_VERSION
    style_profile: str = STYLE_PROFILE


class RadarSemantics(BaseModel):
    semantics: str = "within_clip_visualization_only"
    overall_score: None = None
    disclaimer: str = "仅用于当前片段内部运动稳定性展示，不代表经过验证的综合技术评分。"
    index_method_version: str = "stability-display-index.v1"


class AxisValue(BaseModel):
    axis: str
    display_value: float | None = None
    source_metric_keys: list[str] = Field(default_factory=list)
    source_raw_values: dict = Field(default_factory=dict)
    formula_id: str | None = None
    availability: str  # available | degraded | unavailable


class KinematicArtifactRead(BaseModel):
    artifact_key: str
    artifact_type: str
    module_key: str
    metric_keys: list[str] = Field(default_factory=list)
    status: str
    annotation_frame: int | None = None
    source_video_frame: int | None = None
    frame_range: dict | None = None
    storage_path: str | None = None
    url: str | None = None
    mime_type: str | None = None
    width: int | None = None
    height: int | None = None
    checksum_sha256: str | None = None
    source_annotation_revision: int
    generator_version: str
    status_detail: str | None = None
    skip_reason: str | None = None
    metadata: dict = Field(default_factory=dict)
    presentation: ArtifactPresentation | None = None

    model_config = {"from_attributes": True}


class KinematicArtifactSetRead(BaseModel):
    schema_version: str = SCHEMA_VERSION
    artifact_set_id: int
    annotation_metric_id: int
    normalized_annotation_id: int
    source_annotation_revision: int
    source_metric: SourceMetricRef
    generator: GeneratorRef
    status: str
    created_at: datetime
    artifacts: list[KinematicArtifactRead] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    radar: RadarSemantics | None = None

    model_config = {"from_attributes": True}


class GenerateResponse(BaseModel):
    artifact_set_id: int
    status: str
    created: bool
