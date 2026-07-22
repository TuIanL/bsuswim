from app.schemas.kinematics_report import (
    AthleteContext,
    AnnotationContext,
    AvailableModule,
    FivePageReportSection,
    FivePageReportAssemblyContext,
    Page5Content,
    QualityContext,
    ReportAsset,
    ReportFinding,
    ReportMetric,
    ReportOverviewStat,
    ReportQualityNote,
    ReportSummary,
    SessionContext,
    VideoContext,
    SectionStatus,
)
from .constants import (
    ATTENTION_RANK,
    PAGE_ASSET_ORDER,
    PAGE_FINDINGS_LIMIT,
    PAGE_PLAN,
    SUMMARY_TOP_FINDINGS_LIMIT,
)
from .artifact_projection import (
    collect_skipped_artifact_quality_notes,
    project_to_report_assets_extended,
    select_cross_side_keyframes,
)
from .finding_projection import project_and_sort_findings, sort_findings
from .overview import build_overview_stats
from .retest import build_retest_metrics, resolve_retest_source_metric_keys
from .status import derive_section_status


def _build_athlete_context(ctx) -> dict:
    a = ctx.athlete
    if a is None:
        return {}
    return {
        "id": getattr(a, "id", None),
        "name": getattr(a, "name", None),
        "gender": getattr(a, "gender", None),
        "level": getattr(a, "level", None),
        "stroke_specialty": getattr(a, "stroke_specialty", None),
    }


def _build_session_context(ctx) -> dict:
    s = ctx.session
    if s is None:
        return {}
    sd = getattr(s, "session_date", None)
    return {
        "id": getattr(s, "id", None),
        "title": getattr(s, "title", None),
        "session_date": sd.isoformat() if sd else None,
        "venue": getattr(s, "venue", None),
        "stroke_type": (
            getattr(s, "stroke_type", None).value
            if getattr(s, "stroke_type", None)
            and hasattr(getattr(s, "stroke_type", None), "value")
            else str(getattr(s, "stroke_type", ""))
        ),
        "distance_m": getattr(s, "distance_m", None),
        "pool_length_m": getattr(s, "pool_length_m", None),
    }


def _filter_notes_by_modules(
    notes: list[dict], source_module_keys: list[str]
) -> list[dict]:
    """Keep only artifact quality notes whose module_key is in the page's
    source modules, so a degradation in one module does not leak onto an
    unrelated page."""
    if not source_module_keys:
        return []
    return [n for n in notes if n.get("module_key") in source_module_keys]


def _build_video_context(ctx) -> dict:
    sv = ctx.session_video
    vf = ctx.video_file
    # FPS and resolution are authoritative on SessionVideo. VideoFile has no
    # fps/width/height/duration_sec columns; reading them would always be None
    # (or raise on stricter access). File identity comes from VideoFile only.
    fps = getattr(sv, "fps", None) if sv else None
    resolution = getattr(sv, "resolution", None) if sv else None
    return {
        "session_video_id": getattr(sv, "id", None) if sv else None,
        "video_file_id": getattr(vf, "id", None) if vf else None,
        "original_filename": getattr(vf, "original_filename", None) if vf else None,
        "view_type": getattr(sv, "view_type", None) if sv else None,
        "fps": float(fps) if fps is not None else None,
        "resolution": resolution,
        "duration_sec": None,
    }


def _get_ref_body_length(ctx) -> float | None:
    m = ctx.annotation_metric
    if m is None:
        return None
    quality = (m.metrics or {}).get("quality", {}) if isinstance(m.metrics, dict) else {}
    rbl = quality.get("reference_body_length")
    if isinstance(rbl, dict):
        return rbl.get("value_px")
    return None


def _build_annotation_context(ctx) -> dict:
    ann = ctx.normalized_annotation
    if ann is None:
        return {}
    kpf = getattr(ann, "keypoint_frames", None)
    frame_count = len(kpf) if isinstance(kpf, list) else 0
    eff = getattr(ctx, "_effective_frame_count", frame_count)
    return {
        "normalized_annotation_id": getattr(ann, "id", None),
        "source": getattr(ann, "source", None),
        "revision": getattr(ann, "revision", None),
        "frame_count": frame_count,
        "effective_frame_count": eff,
        "joint_schema": getattr(ann, "joint_schema", None),
        "frame_mapping_status": getattr(ann, "frame_mapping_status", "unknown"),
        "reference_body_length_px": _get_ref_body_length(ctx),
    }


def _build_quality_context(ctx) -> dict:
    ann_metric = getattr(ctx, "annotation_metric", None)
    quality_raw = getattr(ann_metric, "metrics", {}) or {}
    metric_quality = quality_raw.get("quality", {}) if isinstance(quality_raw, dict) else {}

    ann = getattr(ctx, "normalized_annotation", None)
    ann_quality = getattr(ann, "quality", None)
    if hasattr(ann_quality, "model_dump"):
        ann_quality = ann_quality.model_dump(mode="json")

    art_set = getattr(ctx, "artifact_set", None)
    art_status = getattr(art_set, "status", "not_generated") if art_set else "not_generated"

    finding_set = getattr(ctx, "finding_set", None)
    finding_status = getattr(finding_set, "status", "not_generated") if finding_set else "not_generated"

    return {
        "annotation_quality": ann_quality or {},
        "metric_quality": metric_quality or {},
        "artifact_status": art_status,
        "finding_status": finding_status,
    }


def build_analysis_overview_page(
    ctx: FivePageReportAssemblyContext,
    all_report_metrics: dict[str, ReportMetric],
    overview_stats: list[ReportOverviewStat],
    available_modules: list[AvailableModule],
) -> FivePageReportSection:
    plan = PAGE_PLAN[1]
    effective_frame_count = (
        ctx.annotation.effective_frame_count if hasattr(ctx, "annotation") else 0
    )

    content = {
        "athlete": _build_athlete_context(ctx),
        "session": _build_session_context(ctx),
        "video": _build_video_context(ctx),
        "annotation": _build_annotation_context(ctx),
        "quality": _build_quality_context(ctx),
        "available_modules": [am.model_dump(mode="json") for am in available_modules],
        "analysis_boundaries": [
            "本报告基于侧面二维骨架生成。",
            "身体角度以画面水平线为参考，不等同于水面夹角。",
            "待复核发现不构成确定性专业诊断。",
            "本报告不评估力量、推进力、心肺或乳酸能力。",
        ],
    }

    quality_notes = []
    for stat in overview_stats:
        if (
            stat.key == "low_confidence_metric_count"
            and stat.value
            and stat.value > 0
        ):
            quality_notes.append(
                ReportQualityNote(
                    code="low_confidence_metrics_present",
                    level="warning",
                    message=f"存在 {stat.value} 个低置信度指标，部分数据仅供参考。",
                )
            )

    return FivePageReportSection(
        page_number=1,
        page_type=plan["page_type"],
        module_key=plan["module_key"],
        source_module_keys=plan["source_module_keys"],
        title="数据与分析概况",
        status="ready",
        assets=[],
        metrics=[],
        findings=[],
        quality_notes=quality_notes,
        content=content,
    )


def build_body_posture_control_page(
    ctx: FivePageReportAssemblyContext,
    all_report_metrics: dict[str, ReportMetric],
    all_assets: list[ReportAsset],
    findings_by_category: dict[str, list[ReportFinding]],
    artifact_quality_notes: list[dict],
) -> FivePageReportSection:
    from .metric_presentation import PAGE_METRIC_KEYS, select_report_metrics

    plan = PAGE_PLAN[2]
    page_type = plan["page_type"]
    source_keys = plan["source_module_keys"]

    metric_keys = PAGE_METRIC_KEYS.get(page_type, [])
    page_metrics = select_report_metrics(all_report_metrics, metric_keys)

    order = PAGE_ASSET_ORDER.get(page_type, [])
    by_key = {a.key: a for a in all_assets}
    page_assets = [by_key[k] for k in order if k in by_key]
    asset_keys_present = {a.key for a in page_assets}

    page_findings = findings_by_category.get("body_posture", []) + findings_by_category.get("head_trunk", [])
    page_findings = sort_findings(page_findings)[:PAGE_FINDINGS_LIMIT]

    quality_notes: list[ReportQualityNote] = []
    for n in _filter_notes_by_modules(artifact_quality_notes, source_keys):
        quality_notes.append(ReportQualityNote(**n))

    unavailable_metrics = [m for m in page_metrics if m.availability == "unavailable"]
    if unavailable_metrics:
        quality_notes.append(
            ReportQualityNote(
                code="body_posture_head_trunk_metrics_unavailable",
                level="warning",
                message=f"以下指标不可用: {', '.join(m.key for m in unavailable_metrics)}",
            )
        )

    status = derive_section_status(
        page_type,
        page_metrics,
        asset_keys_present,
        getattr(ctx.artifact_set, "status", None),
    )

    return FivePageReportSection(
        page_number=2,
        page_type=page_type,
        module_key=plan["module_key"],
        source_module_keys=source_keys,
        title="身体姿态与头躯干控制",
        status=status,
        assets=page_assets,
        metrics=[m for m in page_metrics if m.availability != "unavailable"],
        findings=page_findings,
        quality_notes=quality_notes,
    )


def build_upper_limb_page(
    ctx: FivePageReportAssemblyContext,
    all_report_metrics: dict[str, ReportMetric],
    all_assets: list[ReportAsset],
    findings_by_category: dict[str, list[ReportFinding]],
    artifact_quality_notes: list[dict],
) -> FivePageReportSection:
    from .metric_presentation import PAGE_METRIC_KEYS, select_report_metrics

    plan = PAGE_PLAN[3]
    page_type = plan["page_type"]
    source_keys = plan["source_module_keys"]

    metric_keys = PAGE_METRIC_KEYS.get(page_type, [])
    page_metrics = select_report_metrics(all_report_metrics, metric_keys)

    elbow_flexion, elbow_extension, _, _ = select_cross_side_keyframes(all_assets)

    order = PAGE_ASSET_ORDER.get(page_type, [])
    by_key = {a.key: a for a in all_assets}
    page_assets: list[ReportAsset] = []
    for k in order:
        if k == "__selected__elbow_flexion" and elbow_flexion is not None:
            page_assets.append(elbow_flexion)
        elif k == "__selected__elbow_extension" and elbow_extension is not None:
            page_assets.append(elbow_extension)
        elif k in by_key:
            page_assets.append(by_key[k])
    asset_keys_present = {a.key for a in page_assets}

    page_findings = findings_by_category.get("upper_limb", [])
    page_findings = sort_findings(page_findings)[:PAGE_FINDINGS_LIMIT]

    quality_notes: list[ReportQualityNote] = []
    for n in _filter_notes_by_modules(artifact_quality_notes, source_keys):
        quality_notes.append(ReportQualityNote(**n))

    unavailable_metrics = [m for m in page_metrics if m.availability == "unavailable"]
    if unavailable_metrics:
        quality_notes.append(
            ReportQualityNote(
                code="upper_limb_metrics_unavailable",
                level="warning",
                message=f"以下指标不可用: {', '.join(m.key for m in unavailable_metrics)}",
            )
        )

    status = derive_section_status(
        page_type,
        page_metrics,
        asset_keys_present,
        getattr(ctx.artifact_set, "status", None),
    )

    return FivePageReportSection(
        page_number=3,
        page_type=page_type,
        module_key=plan["module_key"],
        source_module_keys=source_keys,
        title="上肢运动学",
        status=status,
        assets=page_assets,
        metrics=[m for m in page_metrics if m.availability != "unavailable"],
        findings=page_findings,
        quality_notes=quality_notes,
    )


def build_lower_limb_page(
    ctx: FivePageReportAssemblyContext,
    all_report_metrics: dict[str, ReportMetric],
    all_assets: list[ReportAsset],
    findings_by_category: dict[str, list[ReportFinding]],
    artifact_quality_notes: list[dict],
) -> FivePageReportSection:
    from .metric_presentation import PAGE_METRIC_KEYS, select_report_metrics

    plan = PAGE_PLAN[4]
    page_type = plan["page_type"]
    source_keys = plan["source_module_keys"]

    metric_keys = PAGE_METRIC_KEYS.get(page_type, [])
    page_metrics = select_report_metrics(all_report_metrics, metric_keys)

    _, _, knee_flexion, knee_extension = select_cross_side_keyframes(all_assets)

    order = PAGE_ASSET_ORDER.get(page_type, [])
    by_key = {a.key: a for a in all_assets}
    page_assets: list[ReportAsset] = []
    for k in order:
        if k == "__selected__knee_flexion" and knee_flexion is not None:
            page_assets.append(knee_flexion)
        elif k == "__selected__knee_extension" and knee_extension is not None:
            page_assets.append(knee_extension)
        elif k in by_key:
            page_assets.append(by_key[k])
    asset_keys_present = {a.key for a in page_assets}

    page_findings = findings_by_category.get("lower_limb", [])
    page_findings = sort_findings(page_findings)[:PAGE_FINDINGS_LIMIT]

    quality_notes: list[ReportQualityNote] = []
    for n in _filter_notes_by_modules(artifact_quality_notes, source_keys):
        quality_notes.append(ReportQualityNote(**n))

    unavailable_metrics = [m for m in page_metrics if m.availability == "unavailable"]
    if unavailable_metrics:
        quality_notes.append(
            ReportQualityNote(
                code="lower_limb_metrics_unavailable",
                level="warning",
                message=f"以下指标不可用: {', '.join(m.key for m in unavailable_metrics)}",
            )
        )

    status = derive_section_status(
        page_type,
        page_metrics,
        asset_keys_present,
        getattr(ctx.artifact_set, "status", None),
    )

    return FivePageReportSection(
        page_number=4,
        page_type=page_type,
        module_key=plan["module_key"],
        source_module_keys=source_keys,
        title="下肢运动学",
        status=status,
        assets=page_assets,
        metrics=[m for m in page_metrics if m.availability != "unavailable"],
        findings=page_findings,
        quality_notes=quality_notes,
    )


def _build_objective_summary(index: dict[str, ReportMetric]) -> list[dict]:
    return [
        {
            "key": m.key,
            "label": m.label,
            "value": m.value,
            "display_value": m.display_value,
            "unit": m.unit,
            "availability": m.availability,
        }
        for m in index.values()
        if m.availability == "available"
    ]


def _build_next_capture_suggestions(ctx) -> list[str]:
    suggestions = []
    frame_mapping = (
        getattr(ctx.normalized_annotation, "frame_mapping_status", "unknown")
        if ctx.normalized_annotation
        else "unknown"
    )
    if frame_mapping != "verified":
        suggestions.append(
            "下次采集时提供明确的原视频帧映射，确保标注帧与视频帧精确对应。"
        )
    if ctx.video_file is None:
        suggestions.append(
            "保留与标注文件对应的原始视频文件，以生成带骨骼标注的关键帧图像。"
        )
    return suggestions


def build_review_and_retest_page(
    ctx: FivePageReportAssemblyContext,
    all_report_metrics: dict[str, ReportMetric],
    all_assets: list[ReportAsset],
    all_findings: list[ReportFinding],
    displayed_metric_keys: set[str],
    artifact_quality_notes: list[dict],
) -> FivePageReportSection:
    from .constants import RETEST_CORE_KEYS
    from .retest import build_retest_metrics

    plan = PAGE_PLAN[5]

    order = PAGE_ASSET_ORDER.get("review_and_retest", [])
    by_key = {a.key: a for a in all_assets}
    page_assets = [by_key[k] for k in order if k in by_key]

    sorted_findings = sort_findings(all_findings)
    top_3 = sorted_findings[:3]
    all_limited = sorted_findings[:PAGE_FINDINGS_LIMIT]

    evidence_frames: list[dict] = []
    seen_frames = set()
    for f in sorted_findings:
        for ef in f.evidence_frames:
            key = (ef.annotation_frame, ef.source_video_frame)
            if key not in seen_frames:
                seen_frames.add(key)
                evidence_frames.append(ef.model_dump(mode="json"))
    evidence_frames.sort(
        key=lambda x: (
            x.get("source_video_frame") or 0,
            x.get("annotation_frame") or 0,
        )
    )

    limitations: list[str] = []
    for f in sorted_findings:
        for lim in f.limitations:
            if lim not in limitations:
                limitations.append(lim)

    retest_metrics = build_retest_metrics(
        all_report_metrics, sorted_findings, displayed_metric_keys, RETEST_CORE_KEYS
    )

    next_capture = _build_next_capture_suggestions(ctx)

    radar_semantics = None
    if ctx.artifact_set is not None:
        manifest = getattr(ctx.artifact_set, "manifest", None) or {}
        if isinstance(manifest, dict) and "radar" in manifest:
            radar_semantics = manifest["radar"]
        elif hasattr(manifest, "get"):
            radar_semantics = manifest.get("radar")

    quality_notes: list[ReportQualityNote] = []
    for n in artifact_quality_notes:
        quality_notes.append(ReportQualityNote(**n))
    if radar_semantics is None:
        quality_notes.append(
            ReportQualityNote(
                code="radar_unavailable",
                level="warning",
                message="雷达图不可用",
            )
        )

    content = Page5Content(
        objective_metric_summary=_build_objective_summary(all_report_metrics),
        priority_review_findings=all_limited,
        evidence_frame_index=evidence_frames,
        limitations=limitations,
        next_capture_suggestions=next_capture,
        retest_metrics=retest_metrics,
        radar_semantics=radar_semantics,
    )

    finding_available = ctx.finding_set is not None
    page_status = (
        "partial" if not finding_available or ctx.artifact_set is None else "ready"
    )

    return FivePageReportSection(
        page_number=5,
        page_type=plan["page_type"],
        module_key=plan["module_key"],
        source_module_keys=plan["source_module_keys"],
        title="关键发现与复核建议",
        status=page_status,
        assets=page_assets,
        metrics=[],
        findings=top_3,
        quality_notes=quality_notes,
        content=content.model_dump(mode="json"),
    )
