from __future__ import annotations

from collections.abc import Iterable
from math import ceil
from time import perf_counter
from typing import Any

from app.core.config import Settings
from app.models import ReportInterpretation
from app.schemas.report_interpretation import InterpretationInput, InterpretationOutput


GUARDRAIL_ERROR_CODES = {
    "assertive_claim_forbidden",
    "grounding_reference_invalid",
    "module_reference_mismatch",
    "numeric_claim_ungrounded",
    "output_schema_invalid",
    "training_knowledge_reference_required",
    "visual_claim_ungrounded",
}


def estimate_input_tokens(serialized_input: str) -> int:
    """Conservative mixed Chinese/ASCII estimate used only for budget gating."""
    ascii_chars = sum(1 for char in serialized_input if ord(char) < 128)
    non_ascii_chars = len(serialized_input) - ascii_chars
    return max(1, ceil(ascii_chars / 4) + ceil(non_ascii_chars / 1.5))


def estimate_cost_usd(
    *, input_tokens: int, output_tokens: int, settings: Settings
) -> float:
    cost = (
        input_tokens * settings.ai_interpretation_input_cost_per_million_tokens
        + output_tokens * settings.ai_interpretation_output_cost_per_million_tokens
    ) / 1_000_000
    return round(cost, 8)


def success_validation_metrics(
    output: InterpretationOutput,
    interpretation_input: InterpretationInput,
    validation_result: dict[str, Any],
) -> dict[str, Any]:
    blocks = [output.plain_language_summary]
    blocks.extend(output.module_explanations)
    blocks.extend(output.priority_focus)
    blocks.extend(output.training_suggestions)
    blocks.extend(output.retest_targets)
    grounded = sum(1 for block in blocks if block.fact_refs)
    referenced = {ref for block in blocks for ref in block.fact_refs}
    fact_count = len(interpretation_input.facts)
    return {
        **validation_result,
        "grounded_blocks": grounded,
        "grounding_coverage": round(grounded / len(blocks), 4) if blocks else 1.0,
        "fact_catalog_coverage": round(len(referenced) / fact_count, 4) if fact_count else 1.0,
        "fact_consistency": 1.0,
        "evidence_catalog_count": len(interpretation_input.evidence),
        "evidence_reference_count": sum(len(block.evidence_refs) for block in blocks),
        "evidence_exclusion_count": len(interpretation_input.evidence_exclusions),
        "guardrail_rejected": False,
    }


def usage_metrics(
    usage: dict[str, Any] | None,
    *,
    settings: Settings,
    latency_ms: float,
    retry_count: int = 0,
) -> dict[str, Any]:
    values = dict(usage or {})
    input_tokens = int(values.get("input_tokens") or values.get("prompt_tokens") or 0)
    output_tokens = int(values.get("output_tokens") or values.get("completion_tokens") or 0)
    values.update(
        {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": int(values.get("total_tokens") or input_tokens + output_tokens),
            "retry_count": retry_count,
            "latency_ms": round(latency_ms, 2),
            "estimated_cost_usd": estimate_cost_usd(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                settings=settings,
            ),
        }
    )
    return values


def summarize_observability(records: Iterable[ReportInterpretation]) -> dict[str, float | int]:
    records = list(records)
    total = len(records)
    failures = [record for record in records if record.status == "failed"]
    guardrail_rejections = [
        record for record in failures if record.error_code in GUARDRAIL_ERROR_CODES
    ]
    ready = [record for record in records if record.status == "ready"]
    return {
        "attempts": total,
        "ready": len(ready),
        "failures": len(failures),
        "validation_failure_rate": round(len(failures) / total, 4) if total else 0.0,
        "guardrail_rejection_rate": round(len(guardrail_rejections) / total, 4) if total else 0.0,
        "average_grounding_coverage": round(
            sum(float(record.validation_result.get("grounding_coverage", 0)) for record in ready)
            / len(ready),
            4,
        )
        if ready
        else 0.0,
        "average_latency_ms": round(
            sum(float(record.usage.get("latency_ms", 0)) for record in records) / total, 2
        )
        if total
        else 0.0,
        "total_retries": sum(int(record.usage.get("retry_count", 0)) for record in records),
        "total_tokens": sum(int(record.usage.get("total_tokens", 0)) for record in records),
        "estimated_cost_usd": round(
            sum(float(record.usage.get("estimated_cost_usd", 0)) for record in records), 8
        ),
    }


class GenerationTimer:
    def __init__(self) -> None:
        self._started = perf_counter()

    @property
    def elapsed_ms(self) -> float:
        return (perf_counter() - self._started) * 1000
