import hashlib
import json
from typing import Any

from app.schemas.report_interpretation import (
    InterpretationContext,
    InterpretationFact,
    InterpretationInput,
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


def project_report(report: dict[str, Any]) -> InterpretationInput:
    context = report.get("context") or {}
    session = context.get("session") or {}
    athlete = context.get("athlete") or {}
    video = context.get("video") or {}
    source_revision = _source_revision(report)
    facts: list[InterpretationFact] = []
    seen: set[str] = set()

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
                source_revision=source_revision,
                provenance=metric.get("provenance") or {},
                limitations=limitations,
            ))

        for finding in section.get("findings") or []:
            code = str(finding.get("code") or finding.get("rule_id") or "")
            if not code:
                continue
            finding_id = f"finding:{code}"
            add(InterpretationFact(
                fact_id=finding_id,
                kind="finding",
                module_key=module,
                source_key=code,
                label=str(finding.get("title") or code),
                value=finding.get("status") or "review_required",
                availability="available",
                confidence=finding.get("confidence"),
                source_revision=source_revision,
                provenance={
                    "rule_id": finding.get("rule_id"),
                    "threshold_basis": finding.get("threshold_basis"),
                    "attention_level": finding.get("attention_level"),
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
                    source_revision=source_revision,
                    provenance={
                        "annotation_frame": frame.get("annotation_frame"),
                        "source_video_frame": frame.get("source_video_frame"),
                        "mapping_status": frame.get("mapping_status"),
                        "role": frame.get("role"),
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
    )
