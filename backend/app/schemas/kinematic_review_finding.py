"""二维运动学复核发现（review findings）的 API 与领域 schema。

这些模型表达"待复核发现"，与旧 ``DiagnosticItem`` 严格分离：
- 不设置 ``reason`` / ``training_suggestion``（不越权推断能力或开处方）
- 所有输出 ``status`` 恒为 ``review_required``
- 每条发现携带结构化证据指标、证据帧、置信度、限制与复核问题
"""

from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

REVIEW_FINDINGS_SCHEMA = "swim-2d-review-findings.v1"
THRESHOLD_BASIS_DEFAULT = "project_heuristic_v1"

Availability = Literal["available", "low_confidence", "unavailable"]
AttentionLevel = Literal["low", "medium", "high"]
ConfidenceLevel = Literal["low", "medium", "high"]
FindingCategory = Literal["body_posture", "upper_limb", "lower_limb", "head_trunk"]
FrameRole = Literal[
    "minimum",
    "maximum",
    "peak",
    "trough",
    "spike",
    "max_deviation",
    "representative",
    "context",
]
FindingSetStatus = Literal["generating", "ready", "failed"]


# ── 1.1 证据指标 ──


class FindingEvidenceMetric(BaseModel):
    key: str
    source_metric_keys: list[str]
    derivation: str | None = None
    label: str
    value: float | int | str | None = None
    unit: str | None = None
    availability: Availability
    confidence: float

    comparison: str | None = None
    threshold: float | list[float] | None = None
    reference_basis: str | None = None


# ── 1.2 证据帧 ──


class FindingEvidenceFrame(BaseModel):
    metric_key: str
    annotation_frame: int
    source_video_frame: int | None = None
    time_sec: float | None = None

    role: FrameRole

    value: float | None = None
    extractable: bool = False
    mapping_status: str = "unknown"


# ── 1.3 单条发现 ──


class KinematicReviewFinding(BaseModel):
    code: str
    rule_id: str

    title: str
    category: FindingCategory

    status: Literal["review_required"] = "review_required"
    attention_level: AttentionLevel
    priority: int
    priority_score: float

    evidence_metrics: list[FindingEvidenceMetric] = Field(default_factory=list)
    evidence_frames: list[FindingEvidenceFrame] = Field(default_factory=list)

    confidence: float
    confidence_level: ConfidenceLevel

    limitations: list[str] = Field(default_factory=list)
    review_question: str

    threshold_basis: str = THRESHOLD_BASIS_DEFAULT


# ── 1.4 汇总 ──


class ReviewFindingsSummary(BaseModel):
    review_required_count: int = 0
    categories: dict[str, int] = Field(default_factory=dict)
    highest_priority_code: str | None = None
    highest_attention_level: AttentionLevel | None = None


# ── 1.5 输出包裹 ──


class ReviewFindingsOutput(BaseModel):
    findings: list[KinematicReviewFinding] = Field(default_factory=list)
    summary: ReviewFindingsSummary = Field(default_factory=ReviewFindingsSummary)
    skipped_rules: list[dict] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    matched_rule_ids: list[str] = Field(default_factory=list)


# ── 1.6 生成 / 读取 API schema ──


class ReviewFindingsGenerateResponse(BaseModel):
    finding_set_id: int
    annotation_metric_id: int
    schema_version: str = REVIEW_FINDINGS_SCHEMA
    rule_set: str
    status: FindingSetStatus
    finding_count: int
    created: bool


class ReviewFindingsReadResponse(BaseModel):
    id: int
    annotation_metric_id: int
    normalized_annotation_id: int | None = None
    session_video_id: int | None = None
    schema_version: str = REVIEW_FINDINGS_SCHEMA
    rule_set: str
    rule_version: str
    engine_version: str
    threshold_basis: str
    source_annotation_revision: int | None = None
    generation_signature: str
    status: FindingSetStatus
    findings: list[KinematicReviewFinding] = Field(default_factory=list)
    summary: ReviewFindingsSummary = Field(default_factory=ReviewFindingsSummary)
    skipped_rules: list[dict] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    created_at: Any | None = None


class ReviewFindingsGenerateRequest(BaseModel):
    rule_set: str = "side_2d_kinematics_v1"
    force: bool = False
