"""Golden dataset contract assertion helpers (Change: golden-dataset e2e).

These helpers encode the metric/finding/artifact/report contracts from the
kinematics golden-dataset spec. They operate on plain dicts/JSON so they can
be reused by both the synthetic structure contract and the future real-video
golden E2E without coupling to internal ORM models.

Task coverage: 2.1–2.9 (2.10 PDF page count is asserted separately against the
rendered PDF backend / frontend print protocol).
"""
from __future__ import annotations

import math
from typing import Any, Iterable


def assert_finite_numbers(obj: Any, path: str = "$") -> None:
    """2.1: recursively assert every numeric leaf is finite (no NaN/Inf)."""
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            raise AssertionError(f"non-finite number at {path}: {obj}")
    elif isinstance(obj, int):
        return
    elif isinstance(obj, dict):
        for k, v in obj.items():
            assert_finite_numbers(v, f"{path}.{k}")
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            assert_finite_numbers(v, f"{path}[{i}]")


def assert_canonical_metric_keys(
    metrics: Iterable[dict], canonical_keys: Iterable[str]
) -> None:
    """2.2: metric key set exactly matches calculator.CANONICAL_KEYS."""
    present = {m["key"] for m in metrics}
    expected = set(canonical_keys)
    assert present == expected, (
        f"metric keys mismatch: missing={expected - present}, "
        f"unexpected={present - expected}"
    )


def assert_metric_categories(metrics: Iterable[dict]) -> None:
    """2.2: every metric carries a non-empty category."""
    for m in metrics:
        assert m.get("category"), f"metric {m.get('key')} missing category"


def assert_time_series_ordered(series: list[dict], time_key: str = "t") -> None:
    """2.3: a time series is strictly non-decreasing on its time key."""
    times = [s[time_key] for s in series]
    for i in range(1, len(times)):
        assert times[i] >= times[i - 1], (
            f"time series not ordered at index {i}: {times[i - 1]} -> {times[i]}"
        )


def assert_adjacent_frame_continuity(
    frames: list[dict], value_key: str, max_step: float
) -> None:
    """2.4: adjacent frame deltas stay within an approved continuity bound.

    `frames` MUST already be sorted by frame index. The continuity contract is
    a guard against gross interpolation/serialization corruption, not a
    physiological smoothness assertion.
    """
    values = [f[value_key] for f in frames]
    for i in range(1, len(values)):
        if values[i] is None or values[i - 1] is None:
            continue
        delta = abs(values[i] - values[i - 1])
        assert delta <= max_step, (
            f"frame continuity breach at {i}: delta {delta} > limit {max_step}"
        )


def assert_representative_frame_valid(frame: dict, min_conf: float = 0.0) -> None:
    """2.5: a representative frame has a valid frame index and confidence."""
    assert isinstance(frame.get("annotation_frame"), int) and frame["annotation_frame"] >= 0, (
        f"invalid representative frame index: {frame.get('annotation_frame')}"
    )
    conf = frame.get("confidence", 1.0)
    assert conf >= min_conf, f"representative frame confidence {conf} < {min_conf}"


def assert_source_revision_trace(
    metrics: Iterable[dict], expected_revision: int | None
) -> None:
    """2.6: every metric's source_revision equals the annotation revision."""
    for m in metrics:
        rev = (m.get("provenance") or {}).get("source_revision")
        if rev is None:
            rev = m.get("source_revision")
        assert rev == expected_revision, (
            f"metric {m.get('key')} source_revision {rev} != {expected_revision}"
        )


def assert_artifact_integrity(assets: Iterable[dict]) -> None:
    """2.7: every artifact asset carries file identity + checksum + MIME."""
    for a in assets:
        if a.get("type") in ("image", "video", "chart"):
            assert a.get("url"), f"asset {a.get('key')} missing url"
            assert a.get("mime_type"), f"asset {a.get('key')} missing mime_type"
            meta = a.get("metadata") or {}
            assert meta.get("checksum_sha256") or a.get("checksum_sha256"), (
                f"asset {a.get('key')} missing checksum_sha256"
            )


def assert_five_page_contract(report: dict) -> None:
    """2.8: report has exactly five pages with strictly monotonic page numbers
    and the expected page-type sequence."""
    sections = report["sections"]
    assert len(sections) == 5, f"expected 5 sections, got {len(sections)}"
    page_numbers = [s["page_number"] for s in sections]
    assert page_numbers == [1, 2, 3, 4, 5], f"page numbers {page_numbers}"
    page_types = [s["page_type"] for s in sections]
    expected_types = [
        "analysis_overview",
        "body_posture_control",
        "upper_limb_kinematics",
        "lower_limb_kinematics",
        "review_and_retest",
    ]
    assert page_types == expected_types, f"page types {page_types}"


def assert_no_unsupported_claims(report: dict) -> None:
    """2.9: report must not assert performance scores, predictions, or
    diagnoses beyond the approved kinematic scope.

    Forbidden metric keys (per Decision 13): speed_mps, stroke_length_m, swolf,
    propulsive_force, drag, power_w, hip_depth_cm — these are only allowed in
    analysis_boundaries, limitations, quality_notes, and disclaimer sections.
    """
    approved_categories = {
        "body_posture", "upper_limb", "lower_limb", "head_trunk", "overview",
    }
    claim_bearing_sections = {"summary", "metrics", "findings", "recommendations"}
    forbidden_keys = {
        "speed_mps", "average_speed_mps", "stroke_length_m",
        "swolf", "swolf_value", "propulsive_force", "propulsive",
        "drag", "power_w", "hip_depth_cm",
    }

    for section in report.get("sections", []):
        for m in section.get("metrics", []):
            cat = m.get("category")
            assert cat in approved_categories, (
                f"metric {m.get('key')} has unsupported category: {cat}"
            )
            assert m.get("key") not in forbidden_keys, (
                f"metric makes unsupported claim: {m.get('key')}"
            )

    # Also check summary.top_findings and objective_metric_summary
    if "top_findings" in report.get("summary", {}):
        for f in report["summary"]["top_findings"]:
            for fk in forbidden_keys:
                assert fk not in str(f).lower(), (
                    f"summary.top_findings contains forbidden claim: {fk}"
                )

    if "objective_metric_summary" in report:
        for item in report.get("objective_metric_summary", []) or []:
            if isinstance(item, dict):
                for fk in forbidden_keys:
                    if item.get("key", "") == fk:
                        raise AssertionError(
                            f"objective_metric_summary contains forbidden key: {fk}"
                        )


def assert_pdf_page_count(pdf_path_or_bytes: str | bytes, expected: int = 5) -> None:
    """2.10: PDF page count strictly equals expected (default 5)."""
    try:
        from pypdf import PdfReader
    except ImportError:
        raise AssertionError("pypdf is required for PDF page count assertion")

    reader: PdfReader
    if isinstance(pdf_path_or_bytes, str):
        reader = PdfReader(pdf_path_or_bytes)
    else:
        from io import BytesIO
        reader = PdfReader(BytesIO(pdf_path_or_bytes))

    actual = len(reader.pages)
    assert actual == expected, (
        f"PDF page count mismatch: expected {expected}, got {actual}"
    )


def assert_pdf_semantic_markers(
    pdf_path_or_bytes: str | bytes,
    expected_markers: tuple[str, ...] = (
        "P1 | analysis_overview",
        "P2 | body_posture_control",
        "P3 | upper_limb_kinematics",
        "P4 | lower_limb_kinematics",
        "P5 | review_and_retest",
    ),
) -> None:
    """2.10: each PDF page contains its semantic marker (ASCII, not font-dependent)."""
    try:
        from pypdf import PdfReader
    except ImportError:
        raise AssertionError("pypdf is required for PDF semantic marker assertion")

    reader: PdfReader
    if isinstance(pdf_path_or_bytes, str):
        reader = PdfReader(pdf_path_or_bytes)
    else:
        from io import BytesIO
        reader = PdfReader(BytesIO(pdf_path_or_bytes))

    assert len(reader.pages) >= len(expected_markers), (
        f"PDF has {len(reader.pages)} pages, expected at least {len(expected_markers)}"
    )

    for i, marker in enumerate(expected_markers):
        text = reader.pages[i].extract_text() or ""
        assert marker in text, (
            f"Page {i + 1} missing semantic marker '{marker}'.\n"
            f"Found text: {text[:200]}..."
        )
