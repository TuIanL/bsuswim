"""Five-page kinematics report schemas (swim-report.v1, profile `side_2d_kinematics_5page_v1`).

These models describe the assembled report output — projection, not raw source data.
"""
from datetime import datetime
from enum import StrEnum
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


# ── Report profile constants ──

REPORT_SCHEMA_VERSION = "swim-report.v1"
REPORT_PROFILE = "side_2d_kinematics_5page_v1"
REPORT_PROFILE_VERSION = "1.0.0"
REPORT_MODE = "side_2d_kinematics"
ASSEMBLER_NAME = "five_page_kinematics_report"
ASSEMBLER_VERSION = "1.0.0"

PageNumber = Literal[1, 2, 3, 4, 5]
PageType = Literal[
    "analysis_overview",
    "body_posture_control",
    "upper_limb_kinematics",
    "lower_limb_kinematics",
    "review_and_retest",
]
ModuleKey = Literal[
    "overview",
    "body_posture",
    "upper_limb",
    "lower_limb",
    "head_trunk",
]
PageModuleKey = Literal[
    "overview",
    "body_posture_head_trunk",
    "upper_limb",
    "lower_limb",
    "review_summary",
]

AssemblyStatus = Literal["ready", "partial"]
SectionStatus = Literal["ready", "partial", "unavailable"]
ResolutionStatus = Literal[
    "current_ready",
    "current_partial",
    "current_generating",
    "current_failed",
    "not_generated",
]
SourceMetricCategory = Literal["body_posture", "upper_limb", "lower_limb", "head_trunk"]
MetricAvailability = Literal["available", "low_confidence", "unavailable"]
ReferenceBasis = Literal[
    "screen_horizontal", "joint_geometry", "pixel", "normalized_body_length", "frame_sequence",
]
StatType = Literal["min", "max", "p05", "p50", "p95", "mean", "std"]


class ReportOverviewStatSource(StrEnum):
    NORMALIZED_ANNOTATION = "normalized_annotation"
    METRIC_QUALITY = "metric_quality"
    REPORT_ASSEMBLY = "report_assembly"


# ── ReportMetric ──

class ReportMetric(BaseModel):
    key: str
    label: str
    category: SourceMetricCategory

    value: Any = None
    display_value: str | None = None
    unit: str | None = None

    availability: MetricAvailability = "unavailable"
    confidence: float = 0.0
    sample_count: int = 0

    reference_basis: ReferenceBasis = "screen_horizontal"
    reference_basis_label: str | None = None
    reference_basis_details: dict[str, Any] | None = None

    provenance: dict[str, Any] = Field(default_factory=dict)
    details: dict[str, Any] = Field(default_factory=dict)


# ── ReportAsset ──

class ReportAsset(BaseModel):
    key: str
    type: str
    title: str
    url: str

    artifact_type: str = ""
    module_key: str = ""
    metric_keys: list[str] = Field(default_factory=list)

    annotation_frame: int | None = None
    source_video_frame: int | None = None

    width: int | None = None
    height: int | None = None
    mime_type: str | None = None
    checksum_sha256: str | None = None

    label: str | None = None
    value: str | None = None
    caption: str | None = None

    source_annotation_revision: int | None = None
    generator_version: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


# ── ReportFinding ──

class ReportFindingEvidenceMetric(BaseModel):
    key: str
    source_metric_keys: list[str]
    derivation: str | None = None
    label: str
    value: float | int | str | None = None
    unit: str | None = None
    availability: str
    confidence: float
    comparison: str | None = None
    threshold: float | list[float] | None = None
    reference_basis: str | None = None


class ReportFindingEvidenceFrame(BaseModel):
    metric_key: str
    annotation_frame: int
    source_video_frame: int | None = None
    time_sec: float | None = None
    role: str
    value: float | None = None
    extractable: bool = False
    mapping_status: str = "unknown"


class ReportFinding(BaseModel):
    code: str
    rule_id: str
    title: str
    category: SourceMetricCategory

    status: Literal["review_required"] = "review_required"
    attention_level: str
    priority: int
    priority_score: float

    evidence_metrics: list[ReportFindingEvidenceMetric] = Field(default_factory=list)
    evidence_frames: list[ReportFindingEvidenceFrame] = Field(default_factory=list)

    confidence: float
    confidence_level: str

    limitations: list[str] = Field(default_factory=list)
    review_question: str
    threshold_basis: str


# ── ReportQualityNote ──

class ReportQualityNote(BaseModel):
    code: str
    level: Literal["info", "warning", "error"]
    message: str


# ── ReportOverviewStat ──

class ReportOverviewStat(BaseModel):
    key: str
    label: str
    value: int | float | str | None = None
    display_value: str | None = None
    unit: str | None = None
    source: ReportOverviewStatSource
    provenance: dict[str, Any] = Field(default_factory=dict)


# ── RetestMetric ──

class RetestMetric(BaseModel):
    metric_key: str
    label: str
    current_value: Any = None
    display_value: str | None = None
    unit: str | None = None
    reference_basis: str | None = None

    trigger_metric_key: str | None = None
    derivation: str | None = None
    statistic: StatType | None = None
    reason: str


# ── FivePageReportContext ──

class AthleteContext(BaseModel):
    id: int | None = None
    name: str | None = None
    gender: str | None = None
    level: str | None = None
    stroke_specialty: str | None = None


class SessionContext(BaseModel):
    id: int | None = None
    title: str | None = None
    session_date: str | None = None
    venue: str | None = None
    stroke_type: str | None = None
    distance_m: float | int | None = None
    pool_length_m: float | int | None = None


class VideoContext(BaseModel):
    session_video_id: int | None = None
    video_file_id: int | None = None
    original_filename: str | None = None
    view_type: str | None = None
    fps: float | int | None = None
    resolution: str | None = None
    duration_sec: float | int | None = None


class AnnotationContext(BaseModel):
    normalized_annotation_id: int | None = None
    source: str | None = None
    revision: int | None = None
    frame_count: int | None = None
    effective_frame_count: int | None = None
    joint_schema: str | None = None
    frame_mapping_status: str | None = None
    joint_completeness_ratio: float | None = None
    reference_body_length_px: float | None = None


class QualityContext(BaseModel):
    annotation_quality: dict[str, Any] = Field(default_factory=dict)
    metric_quality: dict[str, Any] = Field(default_factory=dict)
    artifact_status: str | None = None
    finding_status: str | None = None


class AvailableModule(BaseModel):
    module_key: str
    availability: str


class FivePageReportContext(BaseModel):
    athlete: AthleteContext = Field(default_factory=AthleteContext)
    session: SessionContext = Field(default_factory=SessionContext)
    video: VideoContext = Field(default_factory=VideoContext)
    annotation: AnnotationContext = Field(default_factory=AnnotationContext)
    quality: QualityContext = Field(default_factory=QualityContext)
    available_modules: list[AvailableModule] = Field(default_factory=list)
    analysis_boundaries: list[str] = Field(default_factory=list)
    analysis_scope: dict[str, Any] = Field(default_factory=dict)


# ── Report Summary ──

class ReportSummary(BaseModel):
    title: str = ""
    athlete_name: str | None = None
    stroke_type: str | None = None
    usable_module_count: int = 0
    review_required_count: int = 0
    highest_attention_level: str | None = None
    report_disclaimer: str = ""
    top_findings: list[str] = Field(default_factory=list)


# ── Source Trace ──

class AnnotationMetricTrace(BaseModel):
    id: int | None = None
    schema_version: str | None = None
    calculator: str | None = None
    calculator_version: str | None = None
    source_revision: int | None = None
    revision_status: str | None = None
    payload_hash: str | None = None


class ArtifactSetTrace(BaseModel):
    id: int | None = None
    schema_version: str | None = None
    generation_signature: str | None = None
    manifest_sha256: str | None = None
    status: str | None = None
    resolution_status: ResolutionStatus | None = None


class ReviewFindingSetTrace(BaseModel):
    id: int | None = None
    schema_version: str | None = None
    rule_set: str | None = None
    generation_signature: str | None = None
    status: str | None = None
    warning: str | None = None


class AssemblerTrace(BaseModel):
    name: str = ASSEMBLER_NAME
    version: str = ASSEMBLER_VERSION
    profile: str = REPORT_PROFILE
    profile_version: str = REPORT_PROFILE_VERSION


class SourceTrace(BaseModel):
    annotation_metric: AnnotationMetricTrace = Field(default_factory=AnnotationMetricTrace)
    artifact_set: ArtifactSetTrace = Field(default_factory=ArtifactSetTrace)
    review_finding_set: ReviewFindingSetTrace = Field(default_factory=ReviewFindingSetTrace)
    assembler: AssemblerTrace = Field(default_factory=AssemblerTrace)


# ── Section content blocks ──

class Page5Content(BaseModel):
    """Page 5 structured content block."""
    objective_metric_summary: list[dict[str, Any]] = Field(default_factory=list)
    priority_review_findings: list[ReportFinding] = Field(default_factory=list)
    evidence_frame_index: list[dict[str, Any]] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    next_capture_suggestions: list[str] = Field(default_factory=list)
    retest_metrics: list[RetestMetric] = Field(default_factory=list)
    radar_semantics: dict[str, Any] | None = None


# ── Section ──

class FivePageReportSection(BaseModel):
    page_number: PageNumber
    page_type: PageType
    module_key: str
    source_module_keys: list[str] = Field(default_factory=list)
    title: str = ""
    status: SectionStatus = "unavailable"

    assets: list[ReportAsset] = Field(default_factory=list)
    metrics: list[ReportMetric] = Field(default_factory=list)
    findings: list[ReportFinding] = Field(default_factory=list)
    quality_notes: list[ReportQualityNote] = Field(default_factory=list)

    content: dict[str, Any] = Field(default_factory=dict)


# ── Top-level report ──

class FivePageKinematicsReport(BaseModel):
    model_config = ConfigDict(extra="allow")

    schema_version: str = REPORT_SCHEMA_VERSION
    report_profile: str = REPORT_PROFILE
    report_profile_version: str = REPORT_PROFILE_VERSION
    report_mode: str = REPORT_MODE

    status: AssemblyStatus = "partial"
    assembly_status: AssemblyStatus = "partial"

    generated_at: datetime = Field(default_factory=datetime.utcnow)
    generation_signature: str = ""

    summary: ReportSummary = Field(default_factory=ReportSummary)
    context: dict[str, Any] = Field(default_factory=dict)
    sections: list[FivePageReportSection] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    source_trace: SourceTrace = Field(default_factory=SourceTrace)


# ── Assembly Context ──

class ArtifactResolutionResult(BaseModel):
    artifact_set: Any | None = None          # KinematicArtifactSet or None
    resolution_status: ResolutionStatus
    warning_code: str | None = None


class FivePageReportAssemblyContext(BaseModel):
    """Passed into the assembler after resolution and validation."""
    annotation_metric: Any                   # AnnotationMetric
    normalized_annotation: Any               # NormalizedAnnotation
    athlete: Any | None = None               # Athlete
    session: Any | None = None               # TrainingSession
    video_file: Any | None = None            # VideoFile
    session_video: Any | None = None         # SessionVideo
    artifact_set: Any | None = None          # KinematicArtifactSet or None
    finding_set: Any | None = None           # KinematicReviewFindingSet or None
    artifact_resolution: ArtifactResolutionResult = Field(default_factory=lambda: ArtifactResolutionResult(resolution_status="not_generated"))


# ── API request / response ──

class FivePageReportResponse(FivePageKinematicsReport):
    """API response wrapper — same shape as the report."""
    pass
