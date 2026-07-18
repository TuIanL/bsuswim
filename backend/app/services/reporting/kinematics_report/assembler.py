"""Top-level five-page kinematics report assembler."""

from datetime import datetime, timezone
from typing import Optional

from app.schemas.kinematics_report import (
    AnnotationMetricTrace,
    ArtifactResolutionResult,
    ArtifactSetTrace,
    AssemblerTrace,
    AssemblyStatus,
    AvailableModule,
    FivePageKinematicsReport,
    FivePageReportAssemblyContext,
    FivePageReportSection,
    ReportFinding,
    ReportMetric,
    ReportOverviewStat,
    ReportQualityNote,
    ReportSummary,
    ReviewFindingSetTrace,
    SourceTrace,
)
from .constants import ATTENTION_RANK, PAGE_PLAN, SUMMARY_TOP_FINDINGS_LIMIT
from .metric_presentation import build_report_metric_index, select_report_metrics, KINEMATICS_REPORT_METRICS, PAGE_METRIC_KEYS
from .overview import build_overview_stats
from .artifact_projection import (
    project_to_report_assets_extended,
    collect_skipped_artifact_quality_notes,
    select_cross_side_keyframes,
)
from .finding_projection import project_and_sort_findings, group_findings_by_category
from .status import derive_assembly_status
from .signature import compute_report_signature, compute_finding_payload_hash, compute_report_config_hash
from .page_builders import (
    build_analysis_overview_page,
    build_body_posture_control_page,
    build_upper_limb_page,
    build_lower_limb_page,
    build_review_and_retest_page,
)

# Import all configs for report_config_hash
from .constants import (
    ATTENTION_RANK,
    PAGE_ASSET_ORDER,
    PAGE_PLAN,
    PAGE_READINESS_POLICY,
    RETEST_CORE_KEYS,
    SUMMARY_TOP_FINDINGS_LIMIT,
    PAGE_FINDINGS_LIMIT,
)


def _metric_payload_hash(annotation_metric) -> str:
    import hashlib, json
    m = getattr(annotation_metric, "metrics", {}) or {}
    payload = json.dumps(m, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _build_source_trace(ctx: FivePageReportAssemblyContext) -> SourceTrace:
    """Build source trace preserving upstream statuses."""
    m = ctx.annotation_metric
    ann = ctx.normalized_annotation

    revision_status = "current"
    if m and ann:
        expected = getattr(m, "source_revision", None)
        actual = getattr(ann, "revision", None)
        if expected is not None and actual is not None and expected != actual:
            revision_status = "stale"

    # Annotation metric trace
    metric_trace = AnnotationMetricTrace(
        id=getattr(m, "id", None),
        schema_version=getattr(m, "schema_version", None),
        calculator=getattr(m, "calculator", None),
        calculator_version=getattr(m, "calculator_version", None),
        source_revision=getattr(m, "source_revision", None),
        revision_status=revision_status,
        payload_hash=_metric_payload_hash(m),
    )

    # Artifact set trace
    art = ctx.artifact_set
    resolution = ctx.artifact_resolution
    art_trace = ArtifactSetTrace(
        id=getattr(art, "id", None),
        schema_version=getattr(art, "schema_version", None),
        generation_signature=getattr(art, "generation_signature", None),
        manifest_sha256=getattr(art, "manifest_sha256", None),
        status=getattr(art, "status", None),
        resolution_status=resolution.resolution_status if resolution else None,
    )

    # Finding set trace
    fs = ctx.finding_set
    finding_trace = ReviewFindingSetTrace(
        id=getattr(fs, "id", None),
        schema_version=getattr(fs, "schema_version", None),
        rule_set=getattr(fs, "rule_set", None),
        generation_signature=getattr(fs, "generation_signature", None),
        status=getattr(fs, "status", None),
    )

    return SourceTrace(
        annotation_metric=metric_trace,
        artifact_set=art_trace,
        review_finding_set=finding_trace,
        assembler=AssemblerTrace(),
    )


def _build_summary(sections: list[FivePageReportSection], all_findings: list[ReportFinding]) -> ReportSummary:
    usable = sum(1 for s in sections if s.status != "unavailable")
    highest = None
    if all_findings:
        highest = max(all_findings, key=lambda f: (
            -f.priority_score,
            -ATTENTION_RANK.get(f.attention_level, 99),
        )).attention_level if all_findings else None

    top_titles = [f.title for f in all_findings[:SUMMARY_TOP_FINDINGS_LIMIT]]

    return ReportSummary(
        title="自由泳侧面二维运动学分析报告",
        athlete_name=None,
        stroke_type="freestyle",
        usable_module_count=usable,
        review_required_count=len(all_findings),
        highest_attention_level=highest,
        report_disclaimer="本报告基于侧面二维骨架生成，发现均需结合原视频和教练观察复核。",
        top_findings=top_titles,
    )


def _build_warnings(ctx: FivePageReportAssemblyContext, artifact_notes: list[dict]) -> list[str]:
    warnings = []
    resolution = ctx.artifact_resolution
    if resolution:
        if resolution.resolution_status in ("current_generating", "current_failed", "not_generated"):
            warnings.append(resolution.warning_code or "artifacts_issue")
    if ctx.finding_set is None:
        warnings.append("review_findings_not_generated")
    for n in artifact_notes:
        if n.get("code"):
            warnings.append(n["code"])
    return warnings


def _collect_all_displayed_metric_keys(sections: list[FivePageReportSection]) -> set[str]:
    keys = set()
    for s in sections:
        for m in s.metrics:
            keys.add(m.key)
    return keys


def build_five_page_kinematics_report(
    ctx: FivePageReportAssemblyContext,
) -> FivePageKinematicsReport:
    """Assemble the complete five-page kinematics report."""

    # ── Metric index ──
    metric_payload = getattr(ctx.annotation_metric, "metrics", {}) or {}
    summary = metric_payload.get("summary", {}) if isinstance(metric_payload, dict) else {}
    all_report_metrics = build_report_metric_index(summary)

    # ── Artifact projection ──
    all_assets = []
    artifact_quality_notes = []
    if ctx.artifact_set is not None:
        all_assets = project_to_report_assets_extended(ctx.artifact_set)
        artifact_quality_notes = collect_skipped_artifact_quality_notes(ctx.artifact_set)

    # ── Finding projection ──
    all_findings: list[ReportFinding] = []
    findings_by_category: dict[str, list[ReportFinding]] = {}
    if ctx.finding_set is not None:
        raw_findings = getattr(ctx.finding_set, "findings", []) or []
        if raw_findings:
            all_findings = project_and_sort_findings(raw_findings)
            findings_by_category = group_findings_by_category(all_findings)

    # ── Overview stats ──
    ann = ctx.normalized_annotation
    kpf = getattr(ann, "keypoint_frames", None) if ann else None
    effective_frame_count = len(kpf) if isinstance(kpf, list) else 0
    overview_stats = build_overview_stats(ann, {}, all_report_metrics, effective_frame_count)

    # ── Available modules ──
    available_modules = []
    for source_key in ["body_posture", "upper_limb", "lower_limb", "head_trunk"]:
        cat_metrics = [m for m in all_report_metrics.values() if m.category == source_key]
        has_available = any(m.availability == "available" for m in cat_metrics)
        has_low = any(m.availability == "low_confidence" for m in cat_metrics)
        if has_available or has_low:
            availability = "ready" if has_available else "partial"
        else:
            availability = "unavailable"
        available_modules.append(AvailableModule(module_key=source_key, availability=availability))

    # ── Build sections ──

    # Collect all displayed metric keys for retest
    body_posture_keys = PAGE_METRIC_KEYS.get("body_posture_control", [])
    upper_limb_keys = PAGE_METRIC_KEYS.get("upper_limb_kinematics", [])
    lower_limb_keys = PAGE_METRIC_KEYS.get("lower_limb_kinematics", [])
    all_displayed_keys = set(body_posture_keys + upper_limb_keys + lower_limb_keys)

    section_1 = build_analysis_overview_page(ctx, all_report_metrics, overview_stats, available_modules)
    section_2 = build_body_posture_control_page(ctx, all_report_metrics, all_assets, findings_by_category, artifact_quality_notes)
    section_3 = build_upper_limb_page(ctx, all_report_metrics, all_assets, findings_by_category, artifact_quality_notes)
    section_4 = build_lower_limb_page(ctx, all_report_metrics, all_assets, findings_by_category, artifact_quality_notes)
    section_5 = build_review_and_retest_page(ctx, all_report_metrics, all_assets, all_findings, all_displayed_keys, artifact_quality_notes)

    sections = [section_1, section_2, section_3, section_4, section_5]

    # ── Status derivation ──
    resolution_status = ctx.artifact_resolution.resolution_status if ctx.artifact_resolution else None
    finding_available = ctx.finding_set is not None
    assembly_status = derive_assembly_status(sections, resolution_status, finding_available)

    # ── Summary ──
    summary_obj = _build_summary(sections, all_findings)

    # ── Source trace ──
    source_trace = _build_source_trace(ctx)

    # ── Warnings ──
    warnings = _build_warnings(ctx, artifact_quality_notes)

    # ── Generation signature ──
    config_hash = compute_report_config_hash(
        KINEMATICS_REPORT_METRICS, PAGE_METRIC_KEYS, PAGE_PLAN,
        PAGE_READINESS_POLICY, RETEST_CORE_KEYS, PAGE_ASSET_ORDER,
        {"summary": SUMMARY_TOP_FINDINGS_LIMIT, "page": PAGE_FINDINGS_LIMIT},
    )
    finding_payload = compute_finding_payload_hash(ctx.finding_set)
    gen_sig = compute_report_signature(
        annotation_metric_id=getattr(ctx.annotation_metric, "id", 0),
        source_revision=getattr(ctx.annotation_metric, "source_revision", None),
        metric_payload_hash=_metric_payload_hash(ctx.annotation_metric),
        artifact_signature=getattr(ctx.artifact_set, "generation_signature", None),
        artifact_manifest_sha256=getattr(ctx.artifact_set, "manifest_sha256", None),
        finding_signature=getattr(ctx.finding_set, "generation_signature", None),
        finding_payload_hash=finding_payload,
        report_config_hash=config_hash,
    )

    return FivePageKinematicsReport(
        status=assembly_status,
        assembly_status=assembly_status,
        generated_at=datetime.now(timezone.utc),
        generation_signature=gen_sig,
        summary=summary_obj,
        context={},
        sections=sections,
        warnings=warnings,
        source_trace=source_trace,
    )
