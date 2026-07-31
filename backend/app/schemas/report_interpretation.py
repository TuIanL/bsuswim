from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


INTERPRETATION_INPUT_SCHEMA = "swim-report-interpretation-input.v2"
INTERPRETATION_OUTPUT_SCHEMA = "swim-report-interpretation.v2"
PROMPT_POLICY_VERSION = "swim-interpretation-policy.v4"

InterpretationStatus = Literal[
    "not_configured", "pending", "generating", "ready", "failed", "stale"
]
FactKind = Literal["metric", "finding", "frame", "quality", "boundary", "retest"]
ModuleKey = Literal[
    "analysis_overview",
    "body_posture_head_trunk",
    "upper_limb",
    "lower_limb",
    "review_and_retest",
]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class InterpretationFact(StrictModel):
    fact_id: str
    kind: FactKind
    module_key: ModuleKey
    source_key: str
    label: str
    value: Any = None
    unit: str | None = None
    availability: str | None = None
    confidence: float | None = None
    source_revision: int | None = None
    provenance: dict[str, Any] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)


class InterpretationContext(StrictModel):
    stroke_type: str | None = None
    athlete_level: str | None = None
    distance_m: float | int | None = None
    view_type: str | None = None


class KnowledgeEntry(StrictModel):
    knowledge_id: str
    version: str
    title: str
    summary: str
    stroke_types: list[str] = Field(default_factory=list)
    metric_keys: list[str] = Field(default_factory=list)
    finding_codes: list[str] = Field(default_factory=list)
    athlete_levels: list[str] = Field(default_factory=list)
    training_goals: list[str] = Field(default_factory=list)
    contraindications: list[str] = Field(default_factory=list)
    source_title: str
    source_locator: str
    review_status: Literal["draft", "active", "retired"]
    reviewed_by: str | None = None
    reviewed_at: str | None = None


class CurveSummary(StrictModel):
    metric_key: str
    unit: str | None = None
    x_axis: str = "frame"
    points: list[dict[str, float | int | None]] = Field(default_factory=list)
    source_point_count: int = 0
    missing_point_count: int = 0
    sampling: str = "not_available_in_report"


class EvidenceItem(StrictModel):
    evidence_id: str
    asset_key: str
    module_key: ModuleKey
    media_type: Literal["keyframe", "time_series"]
    mime_type: str
    checksum_sha256: str | None = None
    source_annotation_revision: int | None = None
    annotation_frame: int | None = None
    source_video_frame: int | None = None
    metric_keys: list[str] = Field(default_factory=list)
    fact_refs: list[str] = Field(default_factory=list)
    finding_refs: list[str] = Field(default_factory=list)
    selection_reason: str
    curve_summaries: list[CurveSummary] = Field(default_factory=list)


class EvidenceExclusion(StrictModel):
    asset_key: str
    reason: str


class InterpretationInput(StrictModel):
    schema_version: Literal[INTERPRETATION_INPUT_SCHEMA, "swim-report-interpretation-input.v1"] = INTERPRETATION_INPUT_SCHEMA
    base_report_generation_signature: str
    source_revision: int | None = None
    context: InterpretationContext = Field(default_factory=InterpretationContext)
    facts: list[InterpretationFact] = Field(default_factory=list)
    knowledge: list[KnowledgeEntry] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    evidence_exclusions: list[EvidenceExclusion] = Field(default_factory=list)


class InterpretationBlock(StrictModel):
    text: str = Field(min_length=1, max_length=900)
    fact_refs: list[str] = Field(min_length=1)
    knowledge_refs: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)


class ModuleExplanation(InterpretationBlock):
    module_key: Literal["body_posture_head_trunk", "upper_limb", "lower_limb"]


class TrainingSuggestion(InterpretationBlock):
    title: str = Field(min_length=1, max_length=120)
    applicability: str = Field(min_length=1, max_length=300)
    cautions: list[str] = Field(default_factory=list)


class RetestTarget(InterpretationBlock):
    metric_key: str


class InterpretationOutput(StrictModel):
    schema_version: Literal[INTERPRETATION_OUTPUT_SCHEMA, "swim-report-interpretation.v1"] = INTERPRETATION_OUTPUT_SCHEMA
    plain_language_summary: InterpretationBlock
    module_explanations: list[ModuleExplanation] = Field(default_factory=list, max_length=3)
    priority_focus: list[InterpretationBlock] = Field(default_factory=list, max_length=3)
    training_suggestions: list[TrainingSuggestion] = Field(default_factory=list, max_length=3)
    retest_targets: list[RetestTarget] = Field(default_factory=list, max_length=4)
    limitations: list[str] = Field(default_factory=list, max_length=8)


class InterpretationTrace(StrictModel):
    generation_signature: str
    base_report_generation_signature: str
    provider: str
    model: str
    prompt_version: str
    output_schema_version: str
    knowledge_base_version: str
    knowledge_ids: list[str] = Field(default_factory=list)
    execution_mode: Literal["text", "visual"] = "text"
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_exclusion_reasons: list[str] = Field(default_factory=list)
    generated_at: datetime | None = None


class InterpretationError(StrictModel):
    code: str
    message: str
    retryable: bool = False


class InterpretationEnvelope(StrictModel):
    status: InterpretationStatus
    content: InterpretationOutput | None = None
    trace: InterpretationTrace | None = None
    error: InterpretationError | None = None
    can_regenerate: bool = False


class InterpretationGenerateRequest(StrictModel):
    force: bool = False


class InterpretationGenerateResponse(StrictModel):
    interpretation_id: int | None = None
    status: InterpretationStatus
    generation_signature: str | None = None
    reused: bool = False


class ProviderRequest(StrictModel):
    policy: str
    input: InterpretationInput
    output_schema: dict[str, Any]
    evidence_images: dict[str, str] = Field(default_factory=dict)
    visual_mode: bool = False


class ProviderResponse(StrictModel):
    output: dict[str, Any]
    usage: dict[str, Any] = Field(default_factory=dict)
    provider_request_id: str | None = None
