"""诊断相关 API 响应 schema。

复用 ``app.services.diagnostics.models`` 的 pydantic 模型作为响应体，并补充
run / read 端点所需的包裹结构（含 diagnostics_meta 与 summary）。
"""

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.services.diagnostics.models import DiagnosticItem, DiagnosticsSummary, SkippedRuleMeta


class DiagnosticsMeta(BaseModel):
    """diagnostics_meta：写回 raw_result，也随响应返回，供报告与“为何未判断”解释。"""

    rule_set: str
    rule_version: str
    engine_version: str
    matched_rule_ids: list[str] = Field(default_factory=list)
    skipped_rule_ids: list[SkippedRuleMeta] = Field(default_factory=list)
    partial_evaluation_warnings: list[str] = Field(default_factory=list)
    generated_at: Optional[str] = None


class DiagnosticsRunResponse(BaseModel):
    analysis_result_id: int
    rule_set: str
    diagnostics_count: int
    summary: DiagnosticsSummary = Field(default_factory=DiagnosticsSummary)
    diagnostics: list[DiagnosticItem] = Field(default_factory=list)
    diagnostics_meta: DiagnosticsMeta


class DiagnosticsReadResponse(BaseModel):
    analysis_result_id: int
    schema_version: str = "swim-diagnostics.v1"
    rule_set: Optional[str] = None
    diagnostics: list[DiagnosticItem] = Field(default_factory=list)
    summary: DiagnosticsSummary = Field(default_factory=DiagnosticsSummary)
    diagnostics_meta: Optional[DiagnosticsMeta] = None
