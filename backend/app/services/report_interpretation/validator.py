import re
from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP
from math import isclose

from pydantic import ValidationError

from app.schemas.report_interpretation import InterpretationInput, InterpretationOutput


FORBIDDEN_PHRASES = (
    "力量不足",
    "核心能力不足",
    "确诊",
    "证明运动员",
    "说明运动员",
    "一定是",
    "必然导致",
    "综合评分",
    "技术等级",
    "优秀等级",
    "较差等级",
)
NUMBER_PATTERN = re.compile(r"(?<![A-Za-z])[-+]?\d+(?:\.\d+)?")


@dataclass
class InterpretationValidationError(ValueError):
    code: str
    message: str

    def __str__(self) -> str:
        return self.message


def parse_output(raw: dict) -> InterpretationOutput:
    try:
        return InterpretationOutput.model_validate(raw)
    except ValidationError as exc:
        raise InterpretationValidationError("output_schema_invalid", str(exc)) from exc


def _blocks(output: InterpretationOutput):
    yield output.plain_language_summary, None, "summary"
    for item in output.module_explanations:
        yield item, item.module_key, "module"
    for item in output.priority_focus:
        yield item, None, "priority"
    for item in output.training_suggestions:
        yield item, None, "training"
    for item in output.retest_targets:
        yield item, None, "retest"


def _display_candidates(value: float) -> set[float]:
    decimal_value = Decimal(str(value))
    candidates = {value}
    for places in (1, 2, 3):
        quantum = Decimal(1).scaleb(-places)
        candidates.add(float(decimal_value.quantize(quantum, rounding=ROUND_HALF_UP)))
        candidates.add(float(decimal_value.quantize(quantum, rounding=ROUND_DOWN)))
    if abs(value) >= 10:
        candidates.add(float(decimal_value.quantize(Decimal("1"), rounding=ROUND_HALF_UP)))
    return candidates


def _numeric_leaves(value):
    if isinstance(value, dict):
        for item in value.values():
            yield from _numeric_leaves(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _numeric_leaves(item)
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        yield float(value)


def _allowed_numbers(block, facts, knowledge, context_numbers: set[float]) -> set[float]:
    allowed = set(context_numbers)
    for ref in block.fact_refs:
        fact = facts[ref]
        for value in _numeric_leaves(fact.value):
            allowed.update(_display_candidates(value))
        if fact.unit == "frame" and isinstance(fact.value, (list, tuple)):
            allowed.add(float(len(fact.value)))
        if fact.confidence is not None:
            allowed.update(_display_candidates(float(fact.confidence)))
            allowed.update(_display_candidates(float(fact.confidence) * 100))
    for ref in block.knowledge_refs:
        allowed.update(float(item) for item in NUMBER_PATTERN.findall(knowledge[ref].summary))
    return allowed


def _fact_display_numbers(fact) -> set[float]:
    values: set[float] = set()
    for value in _numeric_leaves(fact.value):
        values.update(_display_candidates(value))
    if fact.unit == "frame" and isinstance(fact.value, (list, tuple)):
        values.add(float(len(fact.value)))
    if fact.confidence is not None:
        values.update(_display_candidates(float(fact.confidence)))
        values.update(_display_candidates(float(fact.confidence) * 100))
    return values


def complete_numeric_fact_refs(
    output: InterpretationOutput, interpretation_input: InterpretationInput
) -> list[dict]:
    """Conservatively complete omitted refs without accepting new numeric claims."""
    facts = {fact.fact_id: fact for fact in interpretation_input.facts}
    knowledge = {item.knowledge_id: item for item in interpretation_input.knowledge}
    context_numbers: set[float] = set()
    if interpretation_input.context.distance_m is not None:
        context_numbers.update(
            _display_candidates(float(interpretation_input.context.distance_m))
        )
    completed: list[dict] = []
    for block, expected_module, block_kind in _blocks(output):
        current_allowed = _allowed_numbers(block, facts, knowledge, context_numbers)
        unsupported = {
            float(number)
            for number in NUMBER_PATTERN.findall(block.text)
            if not any(
                isclose(float(number), allowed, rel_tol=0, abs_tol=1e-9)
                for allowed in current_allowed
            )
        }
        if not unsupported:
            continue
        for fact_id in sorted(facts):
            if fact_id in block.fact_refs:
                continue
            fact = facts[fact_id]
            if expected_module and fact.module_key not in (
                expected_module,
                "review_and_retest",
            ):
                continue
            fact_numbers = _fact_display_numbers(fact)
            matched = {
                number
                for number in unsupported
                if any(isclose(number, value, rel_tol=0, abs_tol=1e-9) for value in fact_numbers)
            }
            if len(matched) >= 2 or (matched and fact.label in block.text):
                block.fact_refs.append(fact_id)
                unsupported.difference_update(matched)
                completed.append(
                    {
                        "block": block_kind,
                        "fact_ref": fact_id,
                        "matched_number_count": len(matched),
                    }
                )
            if not unsupported:
                break
    return completed


def validate_output(output: InterpretationOutput, interpretation_input: InterpretationInput) -> dict:
    facts = {fact.fact_id: fact for fact in interpretation_input.facts}
    knowledge = {item.knowledge_id: item for item in interpretation_input.knowledge}
    evidence = {item.evidence_id: item for item in interpretation_input.evidence}
    context_numbers: set[float] = set()
    if interpretation_input.context.distance_m is not None:
        context_numbers.update(
            _display_candidates(float(interpretation_input.context.distance_m))
        )
    checked_blocks = 0
    summary_structure_counts = {
        len(items)
        for items in (
            output.module_explanations,
            output.priority_focus,
            output.training_suggestions,
            output.retest_targets,
        )
        if items
    }
    for block, expected_module, block_kind in _blocks(output):
        checked_blocks += 1
        missing_facts = [ref for ref in block.fact_refs if ref not in facts]
        missing_knowledge = [ref for ref in block.knowledge_refs if ref not in knowledge]
        missing_evidence = [ref for ref in block.evidence_refs if ref not in evidence]
        if missing_facts or missing_knowledge or missing_evidence:
            raise InterpretationValidationError(
                "grounding_reference_invalid",
                f"无效引用 facts={missing_facts}, knowledge={missing_knowledge}, evidence={missing_evidence}",
            )
        if block.evidence_refs and not block.fact_refs:
            raise InterpretationValidationError("visual_claim_ungrounded", "视觉引用必须同时关联事实引用")
        if expected_module:
            invalid_module_refs = [
                ref for ref in block.fact_refs
                if facts[ref].module_key not in (expected_module, "review_and_retest")
                and facts[ref].kind not in ("quality", "boundary")
            ]
            if invalid_module_refs:
                raise InterpretationValidationError("module_reference_mismatch", str(invalid_module_refs))
        if any(phrase in block.text for phrase in FORBIDDEN_PHRASES):
            raise InterpretationValidationError("assertive_claim_forbidden", block.text)

        allowed_numbers = _allowed_numbers(block, facts, knowledge, context_numbers)
        if block_kind == "summary":
            allowed_numbers.update(float(count) for count in summary_structure_counts)
        unsupported_numbers = [
            number
            for number in NUMBER_PATTERN.findall(block.text)
            if not any(
                isclose(float(number), allowed, rel_tol=0, abs_tol=1e-9)
                for allowed in allowed_numbers
            )
        ]
        if unsupported_numbers:
            raise InterpretationValidationError(
                "numeric_claim_ungrounded",
                str(
                    {
                        "block": block_kind,
                        "numbers": unsupported_numbers,
                        "fact_refs": block.fact_refs,
                    }
                ),
            )

    for suggestion in output.training_suggestions:
        if not suggestion.knowledge_refs:
            raise InterpretationValidationError("training_knowledge_reference_required", suggestion.title)

    return {
        "valid": True,
        "checked_blocks": checked_blocks,
        "fact_reference_count": sum(len(block.fact_refs) for block, _, _ in _blocks(output)),
        "knowledge_reference_count": sum(len(block.knowledge_refs) for block, _, _ in _blocks(output)),
        "evidence_reference_count": sum(len(block.evidence_refs) for block, _, _ in _blocks(output)),
    }
