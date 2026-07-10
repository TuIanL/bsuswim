from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

QualityStatus = Literal["valid", "warning", "invalid"]
Severity = Literal["error", "warning", "info"]
ModuleStatus = Literal["ready", "degraded", "blocked"]
MetricAvailability = Literal["available", "low_confidence", "unavailable"]


class SuggestedAction(BaseModel):
    type: str
    label: str
    payload: dict[str, Any] = Field(default_factory=dict)


class QualityIssue(BaseModel):
    code: str
    category: str
    severity: Severity
    blocking: bool = False
    module: str | None = None
    path: str | None = None
    frame: int | None = None
    message: str = ""
    user_message: str = ""
    suggested_action: SuggestedAction | None = None


class ModuleReadiness(BaseModel):
    status: ModuleStatus = "ready"
    blocking_issues: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class QualitySummary(BaseModel):
    blocking_count: int = 0
    error_count: int = 0
    warning_count: int = 0
    info_count: int = 0


class QualityProfileRef(BaseModel):
    id: str
    version: str


class AnnotationQualityReport(BaseModel):
    schema_version: str = "annotation-quality.v2"
    status: QualityStatus = "valid"
    score: int = 0
    source_revision: int = 0
    validator_version: str = "1.0.0"
    profile: 'QualityProfileRef' = Field(default_factory=lambda: QualityProfileRef(id="side_technical_v1", version="1.0.0"))
    validated_at: str = ""
    summary: QualitySummary = Field(default_factory=QualitySummary)
    issues: list[QualityIssue] = Field(default_factory=list)
    module_readiness: dict[str, ModuleReadiness] = Field(default_factory=dict)


class MetricQualityReport(BaseModel):
    schema_version: str = "metric-quality.v1"
    status: QualityStatus = "valid"
    metric_availability: dict[str, MetricAvailability] = Field(default_factory=dict)
    issues: list[QualityIssue] = Field(default_factory=list)
    computed_metric_count: int = 0
    skipped_metric_count: int = 0
    warnings: list[dict[str, str]] = Field(default_factory=list)


class ModuleAvailability(BaseModel):
    body_position: ModuleStatus = "ready"
    arm_entry: ModuleStatus = "ready"
    catch_pull: ModuleStatus = "ready"
    leg_kick: ModuleStatus = "ready"
    efficiency: ModuleStatus = "ready"


class QualityDecision(BaseModel):
    analysis_allowed: bool = True
    report_availability: Literal["full", "degraded", "blocked"] = "full"
    module_availability: ModuleAvailability = Field(default_factory=ModuleAvailability)


class AnalysisQualitySummary(BaseModel):
    schema_version: str = "analysis-quality.v1"
    annotation: dict[str, Any] = Field(default_factory=dict)
    metrics: dict[str, Any] = Field(default_factory=dict)
    decision: QualityDecision = Field(default_factory=QualityDecision)


class ValidationCacheKey(BaseModel):
    annotation_id: int = 0
    source_revision: int = 0
    validator_version: str = ""
    profile_id: str = ""
    profile_version: str = ""


class AnalysisReadiness(BaseModel):
    can_submit: bool = False
    requires_acknowledgement: bool = False
    blocking_issue_count: int = 0
    affected_modules: list[str] = Field(default_factory=list)
