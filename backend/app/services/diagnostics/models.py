"""诊断引擎领域模型（纯 pydantic，不依赖 SQLAlchemy / 数据库）。

这些模型定义规则引擎的稳定输入输出契约：

- ``DiagnosticMetricsContext``：引擎输入（稳定逻辑键的 metrics + manual_tags +
  quality_summary + phase_context），由 ``DiagnosticsMetricsAdapter`` 从
  ``annotation_metrics`` 适配而来。规则 YAML 只消费本契约，永不直接绑定
  ``annotation_metrics.summary`` 的内部键。
- ``DiagnosticItem`` / ``DiagnosticsSummary`` / ``DiagnosticsOutput``：引擎输出。
- ``RuleEvaluationMeta`` / ``SkippedRuleMeta``：规则评估与跳过元数据。
"""

from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

# 严重程度取值（与 YAML severity 分支一致）
Severity = Literal["info", "low", "medium", "high", "critical"]

SEVERITY_ORDER: list[str] = ["critical", "high", "medium", "low", "info"]
SEVERITY_WEIGHT: dict[str, int] = {
    "critical": 100,
    "high": 80,
    "medium": 60,
    "low": 40,
    "info": 20,
}

# 类别权重（用于 priority_score）
CATEGORY_WEIGHT: dict[str, int] = {
    "body_position": 12,
    "catch_pull": 15,
    "arm_entry": 10,
    "leg_kick": 8,
    "efficiency": 14,
}
DEFAULT_CATEGORY_WEIGHT = 5


class DiagnosticItem(BaseModel):
    """单条结构化诊断（教练可读的问题 / 证据 / 原因 / 建议 / 优先级）。"""

    code: str
    title: str
    category: str
    severity: Severity
    priority: int

    evidence: str
    reason: str
    suggestion: str

    metric_refs: list[str] = Field(default_factory=list)
    event_refs: list[str] = Field(default_factory=list)
    manual_tag_refs: list[str] = Field(default_factory=list)

    confidence: float = 1.0
    section_key: Optional[str] = None
    display_order: Optional[int] = None

    recommendation_tags: list[str] = Field(default_factory=list)
    drill_refs: list[str] = Field(default_factory=list)

    # ── 合并 / 调试辅助字段（不参与前端主展示）──
    priority_score: Optional[float] = None
    related_diagnostics: list[dict] = Field(default_factory=list)


class DiagnosticsSummary(BaseModel):
    """诊断总览，供报告首页使用（对应“评价概览 / 关键发现 / 一句话总结”）。"""

    main_strengths: list[str] = Field(default_factory=list)
    main_limitations: list[str] = Field(default_factory=list)
    top_priority: Optional[str] = None
    overall_risk_level: Optional[str] = None
    recommended_focus: list[str] = Field(default_factory=list)


class SkippedRuleMeta(BaseModel):
    """被跳过的规则及其原因（dormant / 缺必需指标 / 禁用）。"""

    id: str
    reason: str
    partial_evaluation_warnings: list[str] = Field(default_factory=list)


class DiagnosticsOutput(BaseModel):
    """引擎完整输出。"""

    diagnostics: list[DiagnosticItem] = Field(default_factory=list)
    summary: DiagnosticsSummary = Field(default_factory=DiagnosticsSummary)
    skipped_rules: list[SkippedRuleMeta] = Field(default_factory=list)
    partial_evaluation_warnings: list[str] = Field(default_factory=list)
    matched_rule_ids: list[str] = Field(default_factory=list)


class DiagnosticMetricsContext(BaseModel):
    """规则引擎的稳定输入契约。

    ``metrics`` 仅含稳定逻辑键（如 ``body_angle_deg`` / ``swolf_value``），
    由 adapter 从 ``annotation_metrics.summary`` 映射而来。规则 YAML 只引用这些键。
    ``phase_context`` 保留原始 ``phase_metrics``，供未来分速度段规则使用（不参与当前评估）。

    质量信息拆为三个命名空间：
    - ``quality_summary``（向后兼容，保留完整聚合快照）
    - ``annotation_quality``（标注输入质量）
    - ``metric_quality``（指标计算质量）
    - ``quality_decision``（聚合可用性决策）
    """

    model_config = ConfigDict(extra="allow")

    metrics: dict[str, Any] = Field(default_factory=dict)
    manual_tags: list[str] = Field(default_factory=list)
    quality_summary: dict = Field(default_factory=dict)
    phase_context: Any = None  # list[dict] 或 None

    # 拆分的质量命名空间
    annotation_quality: dict = Field(default_factory=dict)
    metric_quality: dict = Field(default_factory=dict)
    quality_decision: dict = Field(default_factory=dict)

    # adapter 记录的未能映射/展平的键
    missing_or_unsupported_metrics: list[str] = Field(default_factory=list)
