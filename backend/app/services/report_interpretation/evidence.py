"""Build a privacy-bounded visual evidence bundle from persisted report assets."""

import base64
import hashlib
from io import BytesIO
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.core.config import Settings, get_settings
from app.schemas.report_interpretation import (
    CurveSummary,
    EvidenceExclusion,
    EvidenceItem,
    InterpretationInput,
)


PAGE_MODULES = {
    "body_posture_control": "body_posture_head_trunk",
    "upper_limb_kinematics": "upper_limb",
    "lower_limb_kinematics": "lower_limb",
}


@dataclass
class EvidenceBundle:
    items: list[EvidenceItem]
    exclusions: list[EvidenceExclusion]
    image_data_urls: dict[str, str]


def _fact_refs(input_data: InterpretationInput, module_key: str, metric_keys: list[str]) -> list[str]:
    return [
        fact.fact_id
        for fact in input_data.facts
        if fact.module_key == module_key
        and (not metric_keys or fact.source_key in metric_keys)
    ]


def _finding_refs(input_data: InterpretationInput, module_key: str, metric_keys: list[str]) -> list[str]:
    return [
        fact.fact_id
        for fact in input_data.facts
        if fact.kind == "finding"
        and fact.module_key == module_key
    ]


def _local_asset_path(url: str, settings: Settings) -> Path | None:
    prefix = "/uploads/"
    if not url.startswith(prefix):
        return None
    relative_path = url[len(prefix):]
    candidate = (settings.upload_dir / relative_path).resolve()
    try:
        candidate.relative_to(settings.upload_dir.resolve())
    except ValueError:
        return None
    return candidate


def _sample(points: list[dict[str, Any]], limit: int) -> list[dict[str, float | int | None]]:
    if len(points) <= limit:
        selected = points
    else:
        stride = (len(points) - 1) / (limit - 1)
        selected = [points[round(index * stride)] for index in range(limit)]
    return [
        {
            "frame": point.get("source_video_frame", point.get("annotation_frame", point.get("frame"))),
            "value": point.get("value"),
        }
        for point in selected
    ]


def _curve_summaries(asset: dict[str, Any], settings: Settings) -> list[CurveSummary]:
    """Use only time-series already embedded in the report asset metadata.

    The normal five-page report does not persist full frame data, so a missing
    `series` is represented honestly instead of reopening annotation payloads.
    """
    metadata = asset.get("metadata") or {}
    series = metadata.get("time_series") or metadata.get("series") or {}
    summaries: list[CurveSummary] = []
    for metric_key in asset.get("metric_keys") or []:
        points = list(series.get(metric_key) or [])
        valid = [point for point in points if point.get("value") is not None]
        source_counts = metadata.get("source_point_counts") or {}
        summaries.append(CurveSummary(
            metric_key=metric_key,
            unit=metadata.get("unit") or asset.get("unit"),
            points=_sample(valid, settings.ai_interpretation_max_curve_points),
            source_point_count=int(source_counts.get(metric_key, len(points))),
            missing_point_count=len(points) - len(valid),
            sampling=("uniform_downsample" if len(valid) > settings.ai_interpretation_max_curve_points else "full_embedded_series") if points else "not_available_in_report",
        ))
    return summaries


def _provider_image(asset: dict[str, Any], source: bytes) -> tuple[str, bytes] | None:
    """Return a provider-supported image without persisting a derivative."""
    mime_type = str(asset.get("mime_type") or "application/octet-stream")
    if mime_type in {"image/png", "image/jpeg", "image/webp"}:
        return mime_type, source
    if mime_type != "image/svg+xml":
        return None

    series = (asset.get("metadata") or {}).get("time_series") or {}
    if not isinstance(series, dict) or not series:
        return None

    # DashScope accepts raster images but rejects SVG data URLs. Render the
    # same approved chart series in memory; the source SVG remains unchanged.
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure

    figure = Figure(figsize=(8, 4.5), dpi=100)
    axes = figure.subplots()
    plotted = False
    for metric_key, points in series.items():
        if not isinstance(points, list):
            continue
        coordinates = [
            (point.get("time_sec", point.get("frame")), point.get("value"))
            for point in points
            if isinstance(point, dict)
            and isinstance(point.get("value"), (int, float))
            and isinstance(point.get("time_sec", point.get("frame")), (int, float))
        ]
        if not coordinates:
            continue
        axes.plot(
            [float(x) for x, _ in coordinates],
            [float(y) for _, y in coordinates],
            label=str(metric_key),
            linewidth=1.8,
        )
        plotted = True
    if not plotted:
        return None
    axes.set_title(str(asset.get("key") or "time_series"))
    axes.set_xlabel("time (s)")
    axes.grid(alpha=0.25)
    axes.legend(loc="best", fontsize=8)
    figure.tight_layout()
    buffer = BytesIO()
    FigureCanvasAgg(figure).print_png(buffer)
    return "image/png", buffer.getvalue()


def build_evidence_bundle(report: dict[str, Any], input_data: InterpretationInput, settings: Settings | None = None) -> EvidenceBundle:
    settings = settings or get_settings()
    items: list[EvidenceItem] = []
    exclusions: list[EvidenceExclusion] = []
    image_data_urls: dict[str, str] = {}
    total_bytes = 0
    selected_by_module: dict[str, dict[str, int]] = {}
    selected_asset_keys = {item.asset_key for item in input_data.evidence}

    for section in report.get("sections") or []:
        module_key = PAGE_MODULES.get(str(section.get("page_type")))
        if module_key is None:
            continue
        counters = selected_by_module.setdefault(module_key, {"keyframe": 0, "time_series": 0})
        for asset in section.get("assets") or []:
            artifact_type = str(asset.get("artifact_type") or "")
            media_type = "keyframe" if artifact_type == "annotated_keyframe" else "time_series" if artifact_type == "time_series_chart" else None
            if media_type is None:
                continue
            limit = 2 if media_type == "keyframe" else 1
            asset_key = str(asset.get("key") or "unknown")
            if selected_asset_keys and asset_key not in selected_asset_keys:
                continue
            asset_revision = asset.get("source_annotation_revision")
            if (
                asset_revision is not None
                and input_data.source_revision is not None
                and str(asset_revision) != str(input_data.source_revision)
            ):
                exclusions.append(EvidenceExclusion(asset_key=asset_key, reason="stale_asset"))
                continue
            if counters[media_type] >= limit:
                exclusions.append(EvidenceExclusion(asset_key=asset_key, reason="module_media_limit"))
                continue
            if len(items) >= settings.ai_interpretation_max_evidence_images:
                exclusions.append(EvidenceExclusion(asset_key=asset_key, reason="request_image_limit"))
                continue
            width, height = asset.get("width"), asset.get("height")
            if width and height and int(width) * int(height) > settings.ai_interpretation_max_evidence_image_pixels:
                exclusions.append(EvidenceExclusion(asset_key=asset_key, reason="image_pixel_limit"))
                continue
            path = _local_asset_path(str(asset.get("url") or ""), settings)
            if path is None or not path.is_file():
                exclusions.append(EvidenceExclusion(asset_key=asset_key, reason="asset_unreadable"))
                continue
            data = path.read_bytes()
            if not data or total_bytes + len(data) > settings.ai_interpretation_max_evidence_bytes:
                exclusions.append(EvidenceExclusion(asset_key=asset_key, reason="image_byte_limit"))
                continue
            checksum = hashlib.sha256(data).hexdigest()
            expected_checksum = asset.get("checksum_sha256")
            if expected_checksum and checksum != expected_checksum:
                exclusions.append(EvidenceExclusion(asset_key=asset_key, reason="checksum_mismatch"))
                continue
            metric_keys = list(asset.get("metric_keys") or [])
            evidence_id = f"evidence:{module_key}:{asset_key}"
            provider_image = _provider_image(asset, data)
            if provider_image is None:
                exclusions.append(EvidenceExclusion(asset_key=asset_key, reason="provider_unsupported_media_type"))
                continue
            items.append(EvidenceItem(
                evidence_id=evidence_id,
                asset_key=asset_key,
                module_key=module_key,
                media_type=media_type,
                mime_type=str(asset.get("mime_type") or "application/octet-stream"),
                checksum_sha256=checksum,
                source_annotation_revision=asset.get("source_annotation_revision"),
                annotation_frame=asset.get("annotation_frame"),
                source_video_frame=asset.get("source_video_frame"),
                metric_keys=metric_keys,
                fact_refs=_fact_refs(input_data, module_key, metric_keys),
                finding_refs=_finding_refs(input_data, module_key, metric_keys),
                selection_reason=str(asset.get("selection_reason") or ("diagnostic_keyframe" if media_type == "keyframe" else "module_time_series")),
                curve_summaries=_curve_summaries(asset, settings) if media_type == "time_series" else [],
            ))
            provider_mime_type, provider_data = provider_image
            image_data_urls[evidence_id] = "data:%s;base64,%s" % (
                provider_mime_type,
                base64.b64encode(provider_data).decode("ascii"),
            )
            counters[media_type] += 1
            total_bytes += len(data)
    return EvidenceBundle(items=items, exclusions=exclusions, image_data_urls=image_data_urls)
