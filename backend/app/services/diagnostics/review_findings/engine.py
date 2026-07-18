"""KinematicReviewFindingsEngine：生成二维运动学待复核发现。

设计约束：
- 复用 RuleRegistry 与结构化条件评估器（evaluate_trigger / evaluate_severity_branch）。
- 不复制 evaluator 逻辑（R1）。
- 规则 required 指标处理逻辑键；区分 missing / unavailable / 正常未命中（R2）。
- 每条 finding 的 confidence 由引用指标（metric_meta）计算（R6 置信度 + §6）。
- attention_level 用 evaluate_severity_branch 解析（R1）。
- 排序按 priority_score = priority_base × attention_weight × confidence（§6）。
- 所有输出 status 恒为 review_required。
- 红线护栏（R7）：title 前缀 + 禁用断言短语扫描 title/conclusion/reason。
"""

from typing import Any

from app.services.diagnostics.evaluator import evaluate_severity_branch, evaluate_trigger
from app.services.diagnostics.models import DiagnosticMetricsContext
from app.services.diagnostics.registry import RuleRegistry
from app.services.diagnostics.review_findings.adapter import ReviewAdapterResult
from app.services.diagnostics.review_findings.evidence import EvidenceResolver
from app.schemas.kinematic_review_finding import (
    FindingEvidenceFrame,
    FindingEvidenceMetric,
    KinematicReviewFinding,
    REVIEW_FINDINGS_SCHEMA,
    ReviewFindingsOutput,
    ReviewFindingsSummary,
    THRESHOLD_BASIS_DEFAULT,
)

_ENGINE_VERSION = "review-engine.v1"

_ATTENTION_WEIGHT = {"high": 1.0, "medium": 0.70, "low": 0.40}

_LOW_CONFIDENCE_FACTOR = 0.65

FORBIDDEN_ASSERTIVE_PHRASES = [
    "力量不足",
    "核心能力不足",
    "推进力不足",
    "上肢支撑能力不足",
    "说明运动员",
    "证明运动员",
    "导致阻力增加",
    "必然影响",
]


def _confidence_level(conf: float) -> str:
    if conf >= 0.80:
        return "high"
    if conf >= 0.50:
        return "medium"
    return "low"


def _is_unavailable(meta, key: str) -> bool:
    m = meta.get(key)
    return m is not None and m.availability == "unavailable"


def _validate_forbidden(text: str | None) -> bool:
    if not text:
        return True
    return not any(phrase in text for phrase in FORBIDDEN_ASSERTIVE_PHRASES)


class KinematicReviewFindingsEngine:
    """从 swim-side-kinematics.v1 生成待复核发现。"""

    def __init__(self, registry: RuleRegistry):
        self.registry = registry

    @property
    def engine_version(self) -> str:
        return _ENGINE_VERSION

    def run(
        self,
        adapter_result: ReviewAdapterResult,
        rule_set: str = "side_2d_kinematics_v1",
        metric_dict: dict[str, Any] | None = None,
        canonical_frames: list | None = None,
        mapping_status: str = "unknown",
        threshold_basis: str = THRESHOLD_BASIS_DEFAULT,
    ) -> ReviewFindingsOutput:
        parsed = self.registry.load(rule_set)
        if parsed["meta"].get("output_kind") != "review_finding":
            raise ValueError(f"rule_output_kind_mismatch: expected review_finding, got {parsed['meta'].get('output_kind')}")

        rules = parsed["rules"]
        context: DiagnosticMetricsContext = adapter_result.evaluation_context
        meta = adapter_result.metric_meta

        findings: list[KinematicReviewFinding] = []
        skipped: list[dict] = []
        warnings: list[str] = []
        matched_ids: list[str] = []

        resolver = EvidenceResolver(metric_dict or {}, canonical_frames, mapping_status)

        for rule in rules:
            rule_id = rule["id"]

            if not rule.get("enabled", True):
                skipped.append({"id": rule_id, "reason": "disabled"})
                continue
            if rule.get("status") == "dormant":
                skipped.append({"id": rule_id, "reason": "dormant"})
                continue

            # required 指标逻辑键存在性
            missing = [r for r in rule.get("required_metrics", []) if r not in context.metrics or context.metrics.get(r) is None]
            if missing:
                skipped.append({"id": rule_id, "reason": "missing_metric:" + ",".join(missing)})
                continue

            # unavailable required 指标
            unavail = [r for r in rule.get("required_metrics", []) if _is_unavailable(meta, r)]
            if unavail:
                skipped.append({"id": rule_id, "reason": "unavailable_metric:" + ",".join(unavail)})
                continue

            # trigger
            if not evaluate_trigger(rule.get("condition", {}), context):
                continue

            # attention level
            attention_level, attn_warnings = self._resolve_attention(rule, context)
            warnings.extend(attn_warnings)

            # 证据指标 + 置信度
            evidence_metrics, finding_conf, low_conf = self._build_evidence(
                rule.get("evidence_metric_keys", []), meta
            )

            limitations = list(rule.get("limitations", []))
            if low_conf:
                limitations = limitations + ["部分证据指标可信度较低"]

            # 证据帧
            ef_strategy = rule.get("evidence_frame_strategy") or {}
            frames = resolver.resolve(ef_strategy.get("resolver", ""), ef_strategy.get("limit", 3))

            priority_base = rule.get("priority_base", 50)
            attention_weight = _ATTENTION_WEIGHT.get(attention_level, 0.40)
            priority_score = round(priority_base * attention_weight * finding_conf, 3)

            title = rule.get("title", rule["code"])
            review_question = rule.get("review_question", "")

            # R7 护栏：title 前缀 + 禁用短语扫描（仅 title/conclusion/reason）
            conclusion = None
            if not (title.startswith("疑似") or title.startswith("可能")):
                warnings.append(f"title_not_prefixed:{rule_id}")
            if not _validate_forbidden(title) or not _validate_forbidden(conclusion):
                warnings.append(f"forbidden_assertive_phrase:{rule_id}")

            finding = KinematicReviewFinding(
                code=rule["code"],
                rule_id=rule_id,
                title=title,
                category=rule.get("category", "uncategorized"),
                attention_level=attention_level,
                priority=0,
                priority_score=priority_score,
                evidence_metrics=evidence_metrics,
                evidence_frames=frames,
                confidence=round(finding_conf, 3),
                confidence_level=_confidence_level(finding_conf),
                limitations=limitations,
                review_question=review_question,
                threshold_basis=threshold_basis,
            )
            findings.append(finding)
            matched_ids.append(rule_id)

        # 排序（priority_score DESC, attention DESC, rule_id ASC）
        findings.sort(
            key=lambda f: (
                f.priority_score,
                _ATTENTION_WEIGHT.get(f.attention_level, 0.0),
                0 if f.rule_id is None else 1,
            ),
            reverse=True,
        )
        for i, f in enumerate(findings, start=1):
            f.priority = i

        if not findings and skipped:
            warnings.append("no_evaluable_review_rules")

        summary = self._build_summary(findings)

        return ReviewFindingsOutput(
            findings=findings,
            summary=summary,
            skipped_rules=skipped,
            warnings=warnings,
            matched_rule_ids=matched_ids,
        )

    @staticmethod
    def _resolve_attention(rule: dict, context: DiagnosticMetricsContext) -> tuple[str, list[str]]:
        attn_cfg = rule.get("attention_level") or {}
        # 高 → 低 顺序评估
        for level in ("high", "medium", "low"):
            branch = attn_cfg.get(level)
            if not branch:
                continue
            matched, w = evaluate_severity_branch(branch, context)
            if matched:
                return level, w
        return "low", []

    @staticmethod
    def _build_evidence(keys: list[str], meta: dict) -> tuple[list[FindingEvidenceMetric], float, bool]:
        ev: list[FindingEvidenceMetric] = []
        confs: list[float] = []
        low_conf = False
        for key in keys:
            m = meta.get(key)
            if m is None:
                continue
            if m.availability == "unavailable":
                continue
            if m.availability == "low_confidence":
                low_conf = True
            confs.append(m.confidence)
            ev.append(
                FindingEvidenceMetric(
                    key=key,
                    source_metric_keys=m.source_metric_keys,
                    derivation=m.derivation,
                    label=key,
                    value=m.value,
                    unit=m.unit,
                    availability=m.availability,
                    confidence=m.confidence,
                    comparison=None,
                    threshold=None,
                    reference_basis=m.reference_basis,
                )
            )
        if not confs:
            return ev, 0.0, low_conf
        base = min(confs)
        if low_conf:
            base = round(base * _LOW_CONFIDENCE_FACTOR, 3)
        return ev, base, low_conf

    @staticmethod
    def _build_summary(findings: list[KinematicReviewFinding]) -> ReviewFindingsSummary:
        categories: dict[str, int] = {}
        highest_attn = None
        highest_code = None
        attn_rank = {"high": 3, "medium": 2, "low": 1}
        for f in findings:
            categories[f.category] = categories.get(f.category, 0) + 1
            if highest_attn is None or attn_rank.get(f.attention_level, 0) > attn_rank.get(highest_attn, 0):
                highest_attn = f.attention_level
                highest_code = f.code
        return ReviewFindingsSummary(
            review_required_count=len(findings),
            categories=categories,
            highest_priority_code=highest_code,
            highest_attention_level=highest_attn,
        )
