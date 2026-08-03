import hashlib
import json
from typing import Any

from app.schemas.report_interpretation import (
    FocusCandidate,
    InterpretationContext,
    InterpretationFact,
    InterpretationInput,
    PhaseCycleSummary,
)


PAGE_MODULES = {
    "analysis_overview": "analysis_overview",
    "body_posture_control": "body_posture_head_trunk",
    "upper_limb_kinematics": "upper_limb",
    "lower_limb_kinematics": "lower_limb",
    "review_and_retest": "review_and_retest",
}


def stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def input_hash(value: InterpretationInput) -> str:
    return hashlib.sha256(stable_json(value.model_dump(mode="json")).encode("utf-8")).hexdigest()


def _base_signature(report: dict[str, Any]) -> str:
    trace = report.get("source_trace") or {}
    return str(
        report.get("generation_signature")
        or trace.get("report_generation_signature")
        or ""
    )


def _source_revision(report: dict[str, Any]) -> int | None:
    trace = report.get("source_trace") or {}
    annotation_metric = trace.get("annotation_metric") or {}
    return annotation_metric.get("source_revision") or trace.get("annotation_revision")


def _reference_body_length(report: dict[str, Any]) -> float | None:
    """参考体长（像素）来自 AnnotationContext，五页报告只携带 px 值。

    可靠性信号（sample_count/availability）仅存在于计算器结果，报告上下文中
    以"存在且为正数"作为可用判断；不可用时返回 None 走降级路径。
    """
    annotation = (report.get("context") or {}).get("annotation") or {}
    value = annotation.get("reference_body_length_px")
    if isinstance(value, (int, float)) and value > 0:
        return float(value)
    return None


def _is_numeric(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _normalize_value(value: Any, divisor: float) -> Any:
    if _is_numeric(value):
        return value / divisor
    if isinstance(value, dict):
        return {
            key: _normalize_value(item, divisor)
            for key, item in value.items()
            if _is_numeric(item)
        }
    return None


def _norm_key(source_key: str) -> str:
    for suffix in ("_px_per_frame", "_px"):
        if source_key.endswith(suffix):
            return source_key[: -len(suffix)] + "_norm"
    return f"{source_key}_norm"


_PX_UNITS = ("px", "px/frame")


def _derive_normalized_facts(
    facts: list[InterpretationFact],
    reference_body_length_px: float | None,
    seen: set[str],
) -> None:
    """为像素单位指标（px 距离/波动、px/frame 速度）派生基于参考体长的归一化事实。

    - 参考体长可用：追加 `metric:<key>_norm` 派生事实（值 = px ÷ 体长；
      px → unit=ratio（可表达为百分比），px/frame → unit=body_lengths_per_frame），
      并在原始 px 事实标注"输出应使用归一化值或定性描述"。
    - 参考体长不可用：在原始 px 事实标注"无法归一化，仅可定性描述"。
    - unavailable 或非数值（含全非数值字典）的 px 事实不派生。
    """
    for fact in list(facts):
        if fact.unit not in _PX_UNITS or fact.availability == "unavailable":
            continue
        if _is_numeric(fact.value):
            normalized = fact.value / reference_body_length_px if reference_body_length_px else None
        elif isinstance(fact.value, dict) and any(_is_numeric(item) for item in fact.value.values()):
            normalized = _normalize_value(fact.value, reference_body_length_px) if reference_body_length_px else None
        else:
            continue
        if reference_body_length_px is None:
            note = "参考体长不可用，无法归一化，仅可定性描述，不得输出像素数值"
            if note not in fact.limitations:
                fact.limitations.append(note)
            continue
        norm_key = _norm_key(fact.source_key)
        norm_id = f"metric:{norm_key}"
        if norm_id in seen:
            continue
        norm_unit = "ratio" if fact.unit == "px" else "body_lengths_per_frame"
        suffix = "（占体长比例）" if norm_unit == "ratio" else "（体长/帧）"
        derived = InterpretationFact(
            fact_id=norm_id,
            kind="metric",
            module_key=fact.module_key,
            source_key=norm_key,
            label=f"{fact.label}{suffix}",
            value=normalized,
            unit=norm_unit,
            availability=fact.availability,
            confidence=fact.confidence,
            interpretation_tier=fact.interpretation_tier,
            source_revision=fact.source_revision,
            provenance={
                "derived_from": fact.fact_id,
                "derived_kind": "reference_body_length_normalization",
                "reference_body_length_px": reference_body_length_px,
                "original_unit": fact.unit,
            },
            limitations=["基于参考体长的归一化值，用于替代原始像素跨视频比较"],
            derived_from=fact.fact_id,
        )
        facts.append(derived)
        seen.add(norm_id)
        note = "像素为内部代理单位，用户输出应使用 *_norm 归一化值或定性描述，不得直接输出像素值"
        if note not in fact.limitations:
            fact.limitations.append(note)


def _interpretation_tier(
    availability: str | None,
    confidence: float | None,
    *,
    kind: str,
) -> str:
    if availability == "unavailable":
        return "unavailable"
    if availability in ("low_confidence", "low"):
        return "caution"
    if confidence is not None and confidence < 0.5:
        return "caution"
    if kind == "frame" and availability != "available":
        return "review_only"
    return "primary"


def _focus_candidates(
    facts: list[InterpretationFact],
    findings: list[dict[str, Any]],
) -> list[FocusCandidate]:
    by_id = {fact.fact_id: fact for fact in facts}
    candidates: list[FocusCandidate] = []
    for finding in findings:
        code = str(finding.get("code") or finding.get("rule_id") or "")
        finding_fact = by_id.get(f"finding:{code}")
        if finding_fact is None:
            continue
        attention = {"high": 30, "medium": 20, "low": 10}.get(
            str(finding.get("attention_level") or "low"), 0
        )
        tier_score = {"primary": 20, "caution": 10, "review_only": 0, "unavailable": -20}.get(
            finding_fact.interpretation_tier, 0
        )
        confidence_score = round(max(0.0, min(1.0, float(finding_fact.confidence or 0))) * 10, 2)
        evidence_frames = list(finding.get("evidence_frames") or [])
        verified_frames = sum(1 for frame in evidence_frames if frame.get("mapping_status") == "verified")
        metric_keys = {
            str(frame.get("metric_key"))
            for frame in evidence_frames
            if frame.get("metric_key")
        }
        evidence_metrics = finding.get("evidence_metrics") or []
        for metric in evidence_metrics:
            metric_keys.update(str(key) for key in (metric.get("source_metric_keys") or []) if key)
        metric_facts = [
            fact for fact in facts
            if fact.kind == "metric" and fact.source_key in metric_keys and fact.module_key == finding_fact.module_key
        ]
        if not metric_facts:
            metric_facts = [
                fact for fact in facts
                if fact.kind == "metric" and fact.module_key == finding_fact.module_key
            ][:4]
        repeat_score = 5 if len(evidence_frames) >= 2 else 0
        score = attention + tier_score + confidence_score + min(10, verified_frames * 5) + repeat_score
        fact_refs = [finding_fact.fact_id]
        fact_refs.extend(fact.fact_id for fact in metric_facts[:4] if fact.fact_id not in fact_refs)
        fact_refs.extend(
            fact.fact_id
            for fact in facts
            if fact.kind == "frame"
            and fact.module_key == finding_fact.module_key
            and fact.source_key in metric_keys
            and fact.fact_id not in fact_refs
        )
        candidates.append(FocusCandidate(
            candidate_id=f"focus:{code}",
            module_key=finding_fact.module_key,
            fact_refs=fact_refs,
            label=finding_fact.label,
            rank=0,
            score=score,
            reason=(
                f"attention={finding.get('attention_level') or 'unknown'}; "
                f"tier={finding_fact.interpretation_tier}; verified_frames={verified_frames}; "
                f"repeated_frames={len(evidence_frames)}"
            ),
        ))
    if not candidates:
        for fact in facts:
            if fact.kind == "metric" and fact.interpretation_tier == "primary":
                candidates.append(FocusCandidate(
                    candidate_id=f"focus:metric:{fact.source_key}",
                    module_key=fact.module_key,
                    fact_refs=[fact.fact_id],
                    label=fact.label,
                    rank=0,
                    score=10 + round(float(fact.confidence or 0) * 10, 2),
                    reason="no review finding; primary metric fallback",
                ))
                if len(candidates) >= 3:
                    break
    candidates.sort(key=lambda item: (-item.score, item.candidate_id))
    return [item.model_copy(update={"rank": index + 1}) for index, item in enumerate(candidates[:3])]


def _phase_cycle_summaries(
    report: dict[str, Any],
    facts: list[InterpretationFact],
) -> list[PhaseCycleSummary]:
    summaries: list[PhaseCycleSummary] = []
    for section in report.get("sections") or []:
        content = section.get("content") or {}
        raw_items = content.get("phase_summaries") or content.get("cycle_summaries") or []
        for index, item in enumerate(raw_items[:12]):
            if not isinstance(item, dict):
                continue
            metric_keys = set(item.get("metric_keys") or [])
            fact_refs = [fact.fact_id for fact in facts if fact.source_key in metric_keys]
            summaries.append(PhaseCycleSummary(
                summary_id=str(item.get("summary_id") or item.get("id") or f"phase-cycle:{section.get('page_number')}:{index}"),
                label=str(item.get("label") or item.get("name") or f"阶段/周期 {index + 1}"),
                availability="available",
                frame_start=item.get("frame_start") or item.get("start_frame"),
                frame_end=item.get("frame_end") or item.get("end_frame"),
                repeat_count=item.get("repeat_count") or item.get("cycles"),
                stability=item.get("stability") or item.get("repeatability"),
                sampling=str(item.get("sampling") or "report_summary"),
                fact_refs=fact_refs[:8],
            ))
    return summaries[:12]


def project_report(report: dict[str, Any]) -> InterpretationInput:
    context = report.get("context") or {}
    session = context.get("session") or {}
    athlete = context.get("athlete") or {}
    video = context.get("video") or {}
    source_revision = _source_revision(report)
    facts: list[InterpretationFact] = []
    seen: set[str] = set()
    raw_findings: list[dict[str, Any]] = []

    def add(fact: InterpretationFact) -> None:
        if fact.fact_id not in seen:
            facts.append(fact)
            seen.add(fact.fact_id)

    for section in report.get("sections") or []:
        page_type = str(section.get("page_type") or "analysis_overview")
        module = PAGE_MODULES.get(page_type, "analysis_overview")

        for metric in section.get("metrics") or []:
            key = str(metric.get("key") or "")
            if not key:
                continue
            availability = metric.get("availability")
            value = None if availability == "unavailable" else metric.get("value")
            limitations = []
            if availability == "unavailable":
                limitations.append("该指标不可用，不得据此进行数值判断")
            add(InterpretationFact(
                fact_id=f"metric:{key}",
                kind="metric",
                module_key=module,
                source_key=key,
                label=str(metric.get("label") or key),
                value=value,
                unit=metric.get("unit"),
                availability=availability,
                confidence=metric.get("confidence"),
                interpretation_tier=_interpretation_tier(
                    availability, metric.get("confidence"), kind="metric"
                ),
                source_revision=source_revision,
                provenance={
                    **(metric.get("provenance") or {}),
                    "page_number": section.get("page_number"),
                    "page_type": page_type,
                },
                limitations=limitations,
            ))

        for finding in section.get("findings") or []:
            code = str(finding.get("code") or finding.get("rule_id") or "")
            if not code:
                continue
            finding_id = f"finding:{code}"
            raw_findings.append({**finding, "code": code})
            add(InterpretationFact(
                fact_id=finding_id,
                kind="finding",
                module_key=module,
                source_key=code,
                label=str(finding.get("title") or code),
                value=finding.get("status") or "review_required",
                availability="available",
                confidence=finding.get("confidence"),
                interpretation_tier=_interpretation_tier(
                    "available", finding.get("confidence"), kind="finding"
                ),
                source_revision=source_revision,
                provenance={
                    "rule_id": finding.get("rule_id"),
                    "threshold_basis": finding.get("threshold_basis"),
                    "attention_level": finding.get("attention_level"),
                    "page_number": section.get("page_number"),
                    "page_type": page_type,
                },
                limitations=list(finding.get("limitations") or []),
            ))
            for index, frame in enumerate(finding.get("evidence_frames") or []):
                add(InterpretationFact(
                    fact_id=f"frame:{code}:{index}",
                    kind="frame",
                    module_key=module,
                    source_key=str(frame.get("metric_key") or code),
                    label=f"{finding.get('title') or code}证据帧",
                    value=frame.get("source_video_frame") if frame.get("source_video_frame") is not None else frame.get("annotation_frame"),
                    unit="frame",
                    availability="available" if frame.get("mapping_status") == "verified" else "low_confidence",
                    confidence=finding.get("confidence"),
                    interpretation_tier=_interpretation_tier(
                        "available" if frame.get("mapping_status") == "verified" else "low_confidence",
                        finding.get("confidence"),
                        kind="frame",
                    ),
                    source_revision=source_revision,
                    provenance={
                        "annotation_frame": frame.get("annotation_frame"),
                        "source_video_frame": frame.get("source_video_frame"),
                        "mapping_status": frame.get("mapping_status"),
                        "role": frame.get("role"),
                        "page_number": section.get("page_number"),
                        "page_type": page_type,
                    },
                ))

        for index, note in enumerate(section.get("quality_notes") or []):
            code = str(note.get("code") or f"page-{section.get('page_number')}-{index}")
            add(InterpretationFact(
                fact_id=f"quality:{code}",
                kind="quality",
                module_key=module,
                source_key=code,
                label=str(note.get("message") or code),
                value=note.get("level") or "warning",
                source_revision=source_revision,
                interpretation_tier="caution",
            ))

        if page_type == "analysis_overview":
            for index, boundary in enumerate((section.get("content") or {}).get("analysis_boundaries") or []):
                add(InterpretationFact(
                    fact_id=f"boundary:{index}",
                    kind="boundary",
                    module_key="analysis_overview",
                    source_key=f"boundary-{index}",
                    label=str(boundary),
                    value=str(boundary),
                    source_revision=source_revision,
                    interpretation_tier="caution",
                ))

        if page_type == "review_and_retest":
            for retest in (section.get("content") or {}).get("retest_metrics") or []:
                key = str(retest.get("metric_key") or "")
                if not key:
                    continue
                add(InterpretationFact(
                    fact_id=f"retest:{key}",
                    kind="retest",
                    module_key="review_and_retest",
                    source_key=key,
                    label=str(retest.get("label") or key),
                    value=retest.get("current_value"),
                    unit=retest.get("unit"),
                    availability="available",
                    source_revision=source_revision,
                    limitations=[str(retest.get("reason"))] if retest.get("reason") else [],
                ))

    _derive_normalized_facts(facts, _reference_body_length(report), seen)
    phase_cycle_summaries = _phase_cycle_summaries(report, facts)

    return InterpretationInput(
        base_report_generation_signature=_base_signature(report),
        source_revision=source_revision,
        context=InterpretationContext(
            stroke_type=session.get("stroke_type"),
            athlete_level=athlete.get("level"),
            distance_m=session.get("distance_m"),
            view_type=video.get("view_type"),
        ),
        facts=facts,
        focus_candidates=_focus_candidates(facts, raw_findings),
        phase_cycle_availability="available" if phase_cycle_summaries else "not_available",
        phase_cycle_summaries=phase_cycle_summaries,
    )
