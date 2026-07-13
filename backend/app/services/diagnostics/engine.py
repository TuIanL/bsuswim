"""规则诊断引擎主入口。

流程（Change #5 §8 设计）：
    load rules
      → 逐条规则：disabled/dormant 跳过
      → 校验 required_metrics（缺失 → skipped_rule_ids）
      → 评估 trigger condition（不满足 → 不触发，非错误）
      → 解析 severity（缺失指标的 severity 分支跳过，记 partial warning）
      → 渲染 evidence/reason/suggestion
      → 计算 priority_score
      → 合并 diagnostic_groups（如 R006+R008 → 单条上肢推进主问题）
      → 按 priority 排序
      → 生成 summary
      → 返回 DiagnosticsOutput
"""

from typing import Any, Optional

from app.services.diagnostics.evaluator import evaluate_trigger
from app.services.diagnostics.models import (
    DiagnosticItem,
    DiagnosticsOutput,
    DiagnosticsSummary,
    DiagnosticMetricsContext,
    SkippedRuleMeta,
)
from app.services.diagnostics.recommendation_mapper import RecommendationMapper
from app.services.diagnostics.registry import RuleRegistry
from app.services.diagnostics.severity import resolve_severity, sort_and_assign_priority
from app.services.diagnostics.templates.evidence_templates import FALLBACKS as EVIDENCE_FALLBACKS
from app.services.diagnostics.templates.formatting import render_template
from app.services.diagnostics.templates.reason_templates import FALLBACKS as REASON_FALLBACKS
from app.services.diagnostics.templates.suggestion_templates import FALLBACKS as SUGGESTION_FALLBACKS

_ENGINE_VERSION = "rule-engine.v1"


class RuleBasedDiagnosticsEngine:
    def __init__(self, registry: RuleRegistry):
        self.registry = registry
        self.recommendation_mapper = RecommendationMapper()

    def run(
        self,
        context: DiagnosticMetricsContext,
        rule_set: str = "side_freestyle_v1",
    ) -> DiagnosticsOutput:
        parsed = self.registry.load(rule_set)
        rules = parsed["rules"]
        groups = parsed["groups"]

        diagnostics: list[DiagnosticItem] = []
        skipped: list[SkippedRuleMeta] = []
        matched_ids: list[str] = []
        partial_warnings: list[str] = []

        for rule in rules:
            rule_id = rule["id"]

            # 1) disabled / dormant → 跳过（进 skipped_rule_ids）
            if not rule.get("enabled", True):
                skipped.append(SkippedRuleMeta(id=rule_id, reason="disabled"))
                continue
            if rule.get("status") == "dormant":
                skipped.append(SkippedRuleMeta(id=rule_id, reason="dormant"))
                continue

            # 2) required_metrics 校验（缺失 → skipped_rule_ids，记录细分原因）
            skip_reason = self._check_required(rule, context)
            if skip_reason is not None:
                skipped.append(SkippedRuleMeta(id=rule_id, reason=skip_reason))
                continue

            # 3) trigger condition（不满足 → 不触发；非错误，不进 skipped）
            if not evaluate_trigger(rule.get("condition", {}), context):
                continue

            # 4) severity（缺失指标分支跳过，记 warning）
            severity, sev_warnings = resolve_severity(rule, context)
            partial_warnings.extend(sev_warnings)

            # 5) 渲染文本（YAML 模板优先，缺失回退到 templates/*.py FALLBACKS）
            evidence = render_template(rule.get("evidence_template", ""), context.metrics) or EVIDENCE_FALLBACKS.get(
                rule["code"], ""
            )
            reason = render_template(rule.get("reason_template", ""), context.metrics) or REASON_FALLBACKS.get(
                rule["code"], ""
            )
            suggestion = render_template(
                rule.get("suggestion_template", ""), context.metrics
            ) or SUGGESTION_FALLBACKS.get(rule["code"], "")

            # 记录命中的 manual_tag（用于优先级 bonus）
            manual_tag_refs = self._matched_manual_tags(rule, context)

            item = DiagnosticItem(
                code=rule["code"],
                title=rule.get("title", rule["code"]),
                category=rule.get("category", "uncategorized"),
                severity=severity,
                priority=0,  # 排序后赋值
                evidence=evidence,
                reason=reason,
                suggestion=suggestion,
                metric_refs=list(rule.get("metric_refs", []) or []),
                manual_tag_refs=manual_tag_refs,
                confidence=rule.get("confidence", 1.0),
                section_key=rule.get("section_key"),
                recommendation_tags=list(rule.get("recommendation_tags", []) or []),
            )
            self.recommendation_mapper.enrich(item)
            diagnostics.append(item)
            matched_ids.append(rule_id)

        # 6) 合并 diagnostic_groups（如 R006 + R008 → 单条上肢推进主问题）
        diagnostics = self._apply_groups(diagnostics, groups)

        # 7) 优先级排序 + 赋值
        diagnostics = sort_and_assign_priority(diagnostics)

        # 7.5) 根据指标质量降低诊断置信度
        diagnostics = self._adjust_confidence(diagnostics, context)

        # 8) summary
        summary = self._build_summary(diagnostics)

        return DiagnosticsOutput(
            diagnostics=diagnostics,
            summary=summary,
            skipped_rules=skipped,
            partial_evaluation_warnings=partial_warnings,
            matched_rule_ids=matched_ids,
        )

    # ── required_metrics 校验（含 phase_context 细分原因）──

    def _check_required(self, rule: dict, context: DiagnosticMetricsContext) -> Optional[str]:
        """返回 skip reason（如 ``missing_metric:...``）或 None（全部满足）。"""
        missing_keys: list[str] = []
        for req in rule.get("required_metrics", []) or []:
            if req == "phase_context":
                reason = self._phase_context_skip_reason(context)
                if reason is not None:
                    return reason
                continue
            if req not in context.metrics or context.metrics.get(req) is None:
                missing_keys.append(req)
        if missing_keys:
            return f"missing_metric:{','.join(missing_keys)}"
        return None

    @staticmethod
    def _phase_context_skip_reason(context: DiagnosticMetricsContext) -> Optional[str]:
        """phase_context 缺失/不足时返回细分跳过原因（设计 §2.2）。"""
        pc = context.phase_context
        if not pc:
            return "missing_metric:phase_context"
        if len(pc) < 2:
            return "insufficient_metric:phase_context.speed_buckets"
        has_speed = any(isinstance(p, dict) and p.get("speed_mps") is not None for p in pc)
        if not has_speed:
            return "insufficient_metric:phase_context.distance_markers"
        return None

    @staticmethod
    def _matched_manual_tags(rule: dict, context: DiagnosticMetricsContext) -> list[str]:
        """从 rule.condition 中收集实际命中的 manual_tag（用于优先级 bonus）。"""
        found: list[str] = []
        cond = rule.get("condition", {})

        def _walk(node: Any) -> None:
            if isinstance(node, dict):
                if "manual_tag" in node and node["manual_tag"] in context.manual_tags:
                    found.append(node["manual_tag"])
                for v in node.values():
                    _walk(v)
            elif isinstance(node, list):
                for item in node:
                    _walk(item)

        _walk(cond)
        # 去重保序
        seen = set()
        return [t for t in found if not (t in seen or seen.add(t))]

    # ── 7.5 指标置信度调整 ──

    @staticmethod
    def _adjust_confidence(
        diagnostics: list[DiagnosticItem],
        context: DiagnosticMetricsContext,
    ) -> list[DiagnosticItem]:
        quality_decision = context.quality_decision or {}
        metric_quality = context.metric_quality or {}
        metric_avail = metric_quality.get("metric_availability", {}) if isinstance(metric_quality, dict) else {}
        if not metric_avail:
            return diagnostics

        for diag in diagnostics:
            low_confidence_refs = [
                ref for ref in diag.metric_refs
                if metric_avail.get(ref) == "low_confidence"
            ]
            if low_confidence_refs:
                diag.confidence = round(diag.confidence * 0.5, 2)

        return diagnostics

    # ── diagnostic_groups 合并 ──

    @staticmethod
    def _apply_groups(diagnostics: list[DiagnosticItem], groups: list[dict]) -> list[DiagnosticItem]:
        result = list(diagnostics)
        for g in groups:
            primary_code = g.get("primary")
            related_codes = g.get("related", []) or []
            primary = next((d for d in result if d.code == primary_code), None)
            related = [d for d in result if d.code in related_codes]
            if not primary or not related:
                continue

            # 合并证据 / 原因 / 建议
            primary.evidence = (primary.evidence + " " + "；".join(r.evidence for r in related)).strip()
            primary.reason = (primary.reason + " " + "；".join(r.reason for r in related)).strip()
            primary.suggestion = (primary.suggestion + " " + "；".join(r.suggestion for r in related)).strip()

            # 指标引用合并（去重）
            merged_refs = list(primary.metric_refs)
            for r in related:
                for m in r.metric_refs:
                    if m not in merged_refs:
                        merged_refs.append(m)
            primary.metric_refs = merged_refs

            # 关联诊断（保留 code + evidence 供报告追溯）
            for r in related:
                primary.related_diagnostics.append({"code": r.code, "evidence": r.evidence})

            # 合并后的标题（YAML 可指定 merged_title）
            if g.get("merged_title"):
                primary.title = g["merged_title"]

            # 从结果列表移除被合并的 related
            result = [d for d in result if d not in related]
        return result

    # ── summary 生成 ──

    @staticmethod
    def _build_summary(diagnostics: list[DiagnosticItem]) -> DiagnosticsSummary:
        if not diagnostics:
            return DiagnosticsSummary(overall_risk_level="low")

        severities = [d.severity for d in diagnostics]
        if "critical" in severities or "high" in severities:
            overall_risk_level = "high"
        elif "medium" in severities:
            overall_risk_level = "medium"
        else:
            overall_risk_level = "low"

        main_limitations = [
            d.title for d in diagnostics if d.severity in ("critical", "high", "medium")
        ]
        main_strengths = [d.title for d in diagnostics if d.severity in ("info", "low")]

        recommended_focus: list[str] = []
        for d in diagnostics:
            for tag in d.recommendation_tags:
                if tag not in recommended_focus:
                    recommended_focus.append(tag)

        top_priority = diagnostics[0].title if diagnostics else None

        return DiagnosticsSummary(
            main_strengths=main_strengths,
            main_limitations=main_limitations,
            top_priority=top_priority,
            overall_risk_level=overall_risk_level,
            recommended_focus=recommended_focus,
        )

    @property
    def engine_version(self) -> str:
        return _ENGINE_VERSION
