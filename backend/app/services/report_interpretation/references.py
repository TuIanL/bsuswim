"""Build a non-sensitive, current-report reference catalog for AI output."""

from app.schemas.report_interpretation import (
    InterpretationInput,
    ReferenceCatalogItem,
)


def _anchor(reference_id: str) -> str:
    return "report-ref-" + reference_id.replace(":", "-").replace("/", "-")


def _asset_anchor(asset_key: str) -> str:
    return "report-ref-asset-" + asset_key.replace(":", "-").replace("/", "-")


def build_reference_catalog(
    report: dict,
    interpretation_input: InterpretationInput,
) -> list[ReferenceCatalogItem]:
    """Resolve only identifiers present in the current projected report.

    The catalog contains labels and navigation metadata, never storage paths or
    provider payloads. It is derived again during execution so stale assets
    cannot remain addressable after a report revision changes.
    """
    catalog: list[ReferenceCatalogItem] = []
    for fact in interpretation_input.facts:
        provenance = fact.provenance or {}
        catalog.append(ReferenceCatalogItem(
            reference_id=fact.fact_id,
            reference_type="fact",
            label=fact.label,
            module_key=fact.module_key,
            source_key=fact.source_key,
            page_number=provenance.get("page_number"),
            anchor=_anchor(fact.fact_id),
            annotation_frame=provenance.get("annotation_frame"),
            source_video_frame=provenance.get("source_video_frame"),
            target_available=True,
        ))
    for knowledge in interpretation_input.knowledge:
        catalog.append(ReferenceCatalogItem(
            reference_id=knowledge.knowledge_id,
            reference_type="knowledge",
            label=knowledge.title,
            target_available=False,
        ))
    for evidence in interpretation_input.evidence:
        catalog.append(ReferenceCatalogItem(
            reference_id=evidence.evidence_id,
            reference_type="evidence",
            label=evidence.selection_reason,
            module_key=evidence.module_key,
            source_key=evidence.media_type,
            page_number=None,
            anchor=_asset_anchor(evidence.asset_key),
            asset_key=evidence.asset_key,
            annotation_frame=evidence.annotation_frame,
            source_video_frame=evidence.source_video_frame,
            target_available=True,
        ))
    return catalog
