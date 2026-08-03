import copy
import re
from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP
from math import isclose

from pydantic import ValidationError

from app.schemas.report_interpretation import InterpretationInput, InterpretationOutput
from .knowledge import TRAINING_EVIDENCE_LEVELS


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
PX_UNIT_PATTERN = re.compile(r"(?<![A-Za-z])px\b|像素")
# 训练建议中的剂量/强度数值（距离米、组数、次数、时长）属于推荐内容，不要求
# 可追溯到报告事实；示例：4×25米、6×25米单臂、2组、30秒。
DOSE_UNIT_TOKENS = ("米", "组", "次", "分钟", "秒", "圈", "趟")
DOSE_PATTERN = re.compile(
    r"(?<![A-Za-z])\d+(?:\.\d+)?(?:\s*[×x*]\s*\d+(?:\.\d+)?)*\s*(?:"
    + "|".join(DOSE_UNIT_TOKENS)
    + r")"
)
GENERIC_TRAINING_PATTERNS = ("加强核心", "加强力量", "多练习", "注意姿势", "多做体能")
TRAINING_FACT_KINDS = ("metric", "finding", "retest")
UNCERTAINTY_MARKERS = ("可能", "提示", "建议复核", "与……一致", "与…一致")


@dataclass
class InterpretationValidationError(ValueError):
    code: str
    message: str

    def __str__(self) -> str:
        return self.message


def parse_output(raw: dict) -> InterpretationOutput:
    raw = copy.deepcopy(raw)
    # v3 adds structured display fields while old persisted/provider fixtures
    # may still contain only the legacy text block. Preserve the content and
    # make the missing layers explicit as a review-only fallback.
    if raw.get("schema_version") == "swim-report-interpretation.v3":
        blocks = [raw.get("plain_language_summary")]
        for key in ("module_explanations", "priority_focus", "training_suggestions", "retest_targets"):
            blocks.extend(raw.get(key) or [])
        for block in blocks:
            if not isinstance(block, dict):
                continue
            text = str(block.get("text") or "")
            block.setdefault("observation", text or "当前报告包含可复核事实。")
            block.setdefault("possible_explanations", ["可能反映动作变化，也可能受到数据质量或机位影响。"])
            block.setdefault("potential_impact", "当前结果仅作为训练复核线索，不构成确定性结论。")
            if "module_key" in block or "title" not in block:
                block.setdefault("action", "结合当前报告证据和原视频继续复核。")
            if "title" in block:
                block.setdefault("goal", str(block.get("title") or "改善相关技术指标"))
                block.setdefault("drill", text or "进行与目标指标相关的低强度技术练习。")
                block.setdefault("dose_or_condition", block.get("applicability") or "由教练结合训练量安排")
                block.setdefault("stop_conditions", block.get("cautions") or ["动作质量下降时停止"])
                block.setdefault("success_criterion", "按复测目标在相同条件下复核变化")
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


def _block_text(block) -> str:
    values = [
        block.text,
        getattr(block, "observation", None),
        *(getattr(block, "possible_explanations", None) or []),
        getattr(block, "potential_impact", None),
        getattr(block, "action", None),
        getattr(block, "goal", None),
        getattr(block, "drill", None),
        getattr(block, "dose_or_condition", None),
        *(getattr(block, "stop_conditions", None) or []),
        getattr(block, "success_criterion", None),
    ]
    return "。".join(str(value) for value in values if value)


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
        # ratio 事实允许以百分比（×100）表达，如 0.187 → 18.7%。
        if fact.unit == "ratio":
            for value in _numeric_leaves(fact.value):
                allowed.update(_display_candidates(value * 100))
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
    if fact.unit == "ratio":
        for value in _numeric_leaves(fact.value):
            values.update(_display_candidates(value * 100))
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
            for number in NUMBER_PATTERN.findall(_block_text(block))
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
    structure_signals: list[dict[str, str]] = []
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

        if PX_UNIT_PATTERN.search(_block_text(block)):
            raise InterpretationValidationError("raw_pixel_unit_forbidden", block.text)

        allowed_numbers = _allowed_numbers(block, facts, knowledge, context_numbers)
        if block_kind == "summary":
            allowed_numbers.update(float(count) for count in summary_structure_counts)
        unsupported_numbers = [
            number
            for number in NUMBER_PATTERN.findall(_block_text(block))
            if not any(
                isclose(float(number), allowed, rel_tol=0, abs_tol=1e-9)
                for allowed in allowed_numbers
            )
        ]
        if block_kind == "training":
            # 训练建议中的剂量数字（距离/组数/次数/时长）是推荐内容，豁免事实追溯。
            dose_numbers = {
                float(num)
                for match in DOSE_PATTERN.finditer(block.text)
                for num in NUMBER_PATTERN.findall(match.group(0))
            }
            unsupported_numbers = [
                number for number in unsupported_numbers
                if not any(
                    isclose(float(number), dose, rel_tol=0, abs_tol=1e-9)
                    for dose in dose_numbers
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

        if block_kind in ("module", "priority") and len(block.text) > 60:
            if not any(marker in block.text for marker in UNCERTAINTY_MARKERS):
                structure_signals.append(
                    {"block": block_kind, "signal": "missing_uncertainty_language"}
                )
        if block_kind == "training" and len(_block_text(block)) < 12:
            structure_signals.append({"block": block_kind, "signal": "training_too_brief"})

    has_usable_knowledge = any(
        entry.evidence_level in TRAINING_EVIDENCE_LEVELS for entry in knowledge.values()
    )
    for suggestion in output.training_suggestions:
        if not suggestion.knowledge_refs:
            raise InterpretationValidationError("training_knowledge_reference_required", suggestion.title)
        # 建议必须引用可测量的技术事实（metric/finding/retest），而非仅质量/边界/帧。
        if not any(
            ref in facts and facts[ref].kind in TRAINING_FACT_KINDS
            for ref in suggestion.fact_refs
        ):
            raise InterpretationValidationError("training_fact_kind_required", suggestion.title)
        # 证据等级门控：存在 high/moderate 知识卡时，建议不得只引用 governance/low 卡。
        # 若无任何可用知识卡，允许基于事实的解释降级通过。
        if has_usable_knowledge and not any(
            ref in knowledge and knowledge[ref].evidence_level in TRAINING_EVIDENCE_LEVELS
            for ref in suggestion.knowledge_refs
        ):
            raise InterpretationValidationError("training_knowledge_evidence_insufficient", suggestion.title)
        if any(
            phrase in suggestion.text or phrase in suggestion.title
            for phrase in GENERIC_TRAINING_PATTERNS
        ):
            raise InterpretationValidationError("generic_training_suggestion", suggestion.title)

    if output.schema_version == "swim-report-interpretation.v3":
        for block, _, block_kind in _blocks(output):
            required = [block.observation, block.potential_impact]
            if not block.possible_explanations:
                required.append(None)
            if block_kind in ("summary", "module", "priority"):
                required.append(block.action)
            if block_kind == "training":
                required.extend([
                    block.goal,
                    block.drill,
                    block.dose_or_condition,
                    block.success_criterion,
                ])
                if not block.stop_conditions:
                    required.append(None)
            if any(value in (None, "") for value in required):
                raise InterpretationValidationError(
                    "structured_block_incomplete",
                    f"v3 {block_kind} 缺少结构化解释字段",
                )

        candidate_refs = {
            ref
            for candidate in interpretation_input.focus_candidates
            for ref in candidate.fact_refs
        }
        for priority in output.priority_focus:
            if not candidate_refs.intersection(priority.fact_refs):
                raise InterpretationValidationError(
                    "focus_candidate_invalid",
                    "重点内容没有引用已批准的 focus candidate",
                )

        for block, _, block_kind in _blocks(output):
            referenced_facts = [facts[ref] for ref in block.fact_refs if ref in facts]
            if not referenced_facts:
                continue
            tiers = {fact.interpretation_tier for fact in referenced_facts}
            unavailable_explanation = any(
                marker in _block_text(block) for marker in ("不可用", "缺失", "无法", "待复核")
            )
            review_only_explanation = any(
                marker in _block_text(block) for marker in ("复核", "观察", "确认")
            ) and not NUMBER_PATTERN.findall(_block_text(block))
            if block_kind in ("module", "priority") and tiers <= {"unavailable", "review_only"}:
                if not (unavailable_explanation or review_only_explanation):
                    raise InterpretationValidationError(
                        "low_quality_fact_forbidden",
                        f"{block_kind} 只能引用不可用或待复核事实",
                    )
            if block_kind == "summary" and tiers <= {"unavailable", "review_only"} and not (unavailable_explanation or review_only_explanation):
                raise InterpretationValidationError(
                    "low_quality_fact_forbidden",
                    "summary 只能用明确的不可用或待复核说明引用低质量事实",
                )
            if "caution" in tiers and not any(
                marker in _block_text(block) for marker in UNCERTAINTY_MARKERS
            ):
                raise InterpretationValidationError(
                    "low_quality_fact_forbidden",
                    f"{block_kind} 引用 caution 事实但没有复核条件",
                )

    return {
        "valid": True,
        "checked_blocks": checked_blocks,
        "structure_signals": structure_signals,
        "fact_reference_count": sum(len(block.fact_refs) for block, _, _ in _blocks(output)),
        "knowledge_reference_count": sum(len(block.knowledge_refs) for block, _, _ in _blocks(output)),
        "evidence_reference_count": sum(len(block.evidence_refs) for block, _, _ in _blocks(output)),
    }
