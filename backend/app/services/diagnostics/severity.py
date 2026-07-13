"""严重程度解析、优先级评分与排序。

- ``resolve_severity``：按结构化 severity 配置（critical→high→medium→low 降序）取首个命中分支；
  缺失指标的 severity 分支被跳过（记 warning），不使整条规则失败。
- ``compute_priority_score``：severity + category + manual_tag + multi_metric 权重之和。
- ``sort_and_assign_priority``：按 priority_score 降序（severity 权重兜底）排序并赋 1..N。
"""

from typing import Any

from app.services.diagnostics.evaluator import evaluate_severity_branch
from app.services.diagnostics.models import (
    CATEGORY_WEIGHT,
    DEFAULT_CATEGORY_WEIGHT,
    SEVERITY_ORDER,
    SEVERITY_WEIGHT,
    DiagnosticItem,
    DiagnosticMetricsContext,
)

# severity 评估优先顺序（高 → 低）
_SEVERITY_EVAL_ORDER = ["critical", "high", "medium", "low"]

_MANUAL_TAG_BONUS = 8
_MULTI_METRIC_BONUS = 8  # 命中 ≥2 个 metric_refs 时附加


def resolve_severity(rule: dict, context: DiagnosticMetricsContext) -> tuple[str, list[str]]:
    """返回 (severity, partial_warnings)。无分支命中时回落到 low。"""
    sev_cfg = rule.get("severity") or {}
    warnings: list[str] = []
    for level in _SEVERITY_EVAL_ORDER:
        branch = sev_cfg.get(level)
        if not branch:
            continue
        matched, w = evaluate_severity_branch(branch, context)
        warnings.extend(w)
        if matched:
            return level, warnings
    return "low", warnings


def compute_priority_score(
    severity: str,
    category: str,
    metric_refs: list[str],
    manual_tag_refs: list[str],
) -> int:
    """priority_score = severity + category + manual_tag + multi_metric 权重。"""
    score = SEVERITY_WEIGHT.get(severity, 20)
    score += CATEGORY_WEIGHT.get(category, DEFAULT_CATEGORY_WEIGHT)
    if manual_tag_refs:
        score += _MANUAL_TAG_BONUS
    if len(metric_refs) >= 2:
        score += _MULTI_METRIC_BONUS
    return score


def sort_and_assign_priority(diagnostics: list[DiagnosticItem]) -> list[DiagnosticItem]:
    """按优先级降序排序，赋 ``priority = 1,2,3...``；后台保留 ``priority_score``。"""
    for d in diagnostics:
        if d.priority_score is None:
            d.priority_score = compute_priority_score(
                d.severity, d.category, d.metric_refs, d.manual_tag_refs
            )

    diagnostics.sort(
        key=lambda d: (d.priority_score or 0, SEVERITY_WEIGHT.get(d.severity, 0)),
        reverse=True,
    )
    for i, d in enumerate(diagnostics, start=1):
        d.priority = i
        d.display_order = i
    return diagnostics
