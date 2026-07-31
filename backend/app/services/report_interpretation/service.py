from datetime import datetime, timedelta, timezone
import json
from typing import Any, Callable

from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import SessionLocal
from app.models import ReportInterpretation, ReportMetadata
from app.schemas.report_interpretation import (
    INTERPRETATION_OUTPUT_SCHEMA,
    PROMPT_POLICY_VERSION,
    EvidenceExclusion,
    InterpretationEnvelope,
    InterpretationError,
    InterpretationInput,
    InterpretationOutput,
    InterpretationTrace,
    ProviderRequest,
)
from .knowledge import KnowledgeRegistry
from .evidence import build_evidence_bundle
from .projector import project_report
from .provider import InterpretationProvider, ProviderError, build_provider
from .prompt import SYSTEM_POLICY
from .signature import generation_signature
from .telemetry import (
    GUARDRAIL_ERROR_CODES,
    GenerationTimer,
    estimate_cost_usd,
    estimate_input_tokens,
    success_validation_metrics,
    usage_metrics,
)
from .validator import (
    InterpretationValidationError,
    complete_numeric_fact_refs,
    parse_output,
    validate_output,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _base_signature(report_data: dict) -> str:
    trace = report_data.get("source_trace") or {}
    return str(report_data.get("generation_signature") or trace.get("report_generation_signature") or "")


def _serialized_input(value: InterpretationInput) -> str:
    return json.dumps(value.model_dump(mode="json"), ensure_ascii=False, separators=(",", ":"))


def _fit_evidence_to_input_budget(value: InterpretationInput, max_chars: int) -> None:
    """Reduce visual context before rejecting a valid factual report.

    Facts and knowledge are never truncated. Curve points are reduced first,
    then the least-prioritized (last) visual asset is excluded with an audit
    reason. This protects the existing text interpretation path.
    """
    def downsample(curve: Any, limit: int, sampling: str) -> None:
        if len(curve.points) <= limit:
            return
        if limit <= 1:
            curve.points = [curve.points[-1]]
            curve.sampling = sampling
            return
        last_point = curve.points[-1]
        stride = max(1, (len(curve.points) - 1) // (limit - 1))
        curve.points = curve.points[::stride][:limit]
        if curve.points[-1] != last_point:
            curve.points[-1] = last_point
        curve.sampling = sampling

    # The source report can contain a very dense series. Limit it before the
    # first JSON serialization; otherwise the budget loop itself becomes an
    # expensive O(n) operation over the complete per-frame dataset.
    for item in value.evidence:
        for curve in item.curve_summaries:
            downsample(curve, 64, "initial_input_budget_downsample")

    while len(_serialized_input(value)) > max_chars:
        curves = [curve for item in value.evidence for curve in item.curve_summaries if curve.points]
        if curves:
            curve = max(curves, key=lambda item: len(item.points))
            if len(curve.points) == 1:
                curve.points = []
                curve.sampling = "omitted_for_input_budget"
            else:
                downsample(curve, max(1, len(curve.points) // 2), "budget_downsample")
            continue
        if value.evidence:
            removed = value.evidence.pop()
            value.evidence_exclusions.append(
                EvidenceExclusion(
                    asset_key=removed.asset_key,
                    reason="interpretation_input_budget",
                )
            )
            continue
        return


def prepare_input(
    report_data: dict,
    settings: Settings,
    registry: KnowledgeRegistry | None = None,
) -> tuple[InterpretationInput, KnowledgeRegistry, str, str]:
    registry = registry or KnowledgeRegistry()
    projected = project_report(report_data)
    projected.knowledge = registry.retrieve(
        projected,
        limit=settings.ai_interpretation_max_knowledge_items,
    )
    bundle = build_evidence_bundle(report_data, projected, settings)
    projected.evidence = bundle.items
    projected.evidence_exclusions = bundle.exclusions
    _fit_evidence_to_input_budget(projected, settings.ai_interpretation_max_input_chars)
    serialized = _serialized_input(projected)
    if len(serialized) > settings.ai_interpretation_max_input_chars:
        raise ProviderError("interpretation_input_too_large", "AI 解读输入超过部署上限", False)
    budget_input = "\n".join(
        (
            SYSTEM_POLICY,
            serialized,
            json.dumps(InterpretationOutput.model_json_schema(), separators=(",", ":")),
        )
    )
    estimated_input_tokens = estimate_input_tokens(budget_input)
    maximum_cost = estimate_cost_usd(
        input_tokens=estimated_input_tokens,
        output_tokens=settings.ai_interpretation_max_output_tokens or 0,
        settings=settings,
    )
    if maximum_cost > settings.ai_interpretation_max_estimated_cost_usd:
        raise ProviderError("interpretation_cost_limit_exceeded", "AI 解读预计费用超过部署上限", False)
    signature, current_input_hash = generation_signature(projected, settings, registry.version)
    return projected, registry, signature, current_input_hash


def _next_attempt(db: Session, report_id: int, signature: str) -> int:
    value = db.scalar(
        select(func.max(ReportInterpretation.attempt)).where(
            ReportInterpretation.report_metadata_id == report_id,
            ReportInterpretation.generation_signature == signature,
        )
    )
    return int(value or 0) + 1


def enforce_rate_limit(db: Session, user_id: int, settings: Settings) -> None:
    since = _utcnow() - timedelta(hours=1)
    count = db.scalar(
        select(func.count(ReportInterpretation.id)).where(
            ReportInterpretation.requested_by_user_id == user_id,
            ReportInterpretation.created_at >= since,
        )
    ) or 0
    if count >= settings.ai_interpretation_rate_limit_per_hour:
        raise ProviderError("interpretation_rate_limited", "AI 解读生成请求过于频繁", True)


def create_or_reuse_interpretation(
    db: Session,
    report: ReportMetadata,
    *,
    requested_by_user_id: int | None,
    force: bool = False,
    settings: Settings | None = None,
    registry: KnowledgeRegistry | None = None,
) -> tuple[ReportInterpretation | None, bool]:
    settings = settings or get_settings()
    if not settings.ai_interpretation_configured:
        return None, False

    try:
        # Do not let an abandoned report lock keep an API request waiting
        # indefinitely. The client can make an explicit retry after the writer
        # releases the row.
        locked = db.scalar(
            select(ReportMetadata)
            .where(ReportMetadata.id == report.id)
            .with_for_update(nowait=True)
        ) or report
    except OperationalError as exc:
        db.rollback()
        raise ProviderError(
            "interpretation_queue_busy",
            "报告正在被另一项操作占用，请稍后重新生成 AI 解读",
            True,
        ) from exc
    projected, registry, signature, current_input_hash = prepare_input(
        locked.report_data or {}, settings, registry
    )
    if not projected.base_report_generation_signature:
        raise ProviderError("base_report_signature_missing", "基础报告缺少 generation signature", False)
    if not projected.facts:
        raise ProviderError("no_interpretable_facts", "基础报告没有可解释事实", False)

    existing = db.scalar(
        select(ReportInterpretation)
        .where(
            ReportInterpretation.report_metadata_id == locked.id,
            ReportInterpretation.generation_signature == signature,
            ReportInterpretation.status.in_(["ready", "generating", "pending"]),
        )
        .order_by(ReportInterpretation.attempt.desc())
    )
    if existing is not None and not force:
        return existing, True
    if requested_by_user_id is not None:
        enforce_rate_limit(db, requested_by_user_id, settings)

    record = ReportInterpretation(
        report_metadata_id=locked.id,
        requested_by_user_id=requested_by_user_id,
        base_report_generation_signature=projected.base_report_generation_signature,
        input_hash=current_input_hash,
        generation_signature=signature,
        attempt=_next_attempt(db, locked.id, signature),
        force_requested=force,
        provider=settings.ai_interpretation_provider,
        model=settings.ai_interpretation_model,
        model_parameters={
            "temperature": settings.ai_interpretation_temperature,
            "max_output_tokens": settings.ai_interpretation_max_output_tokens,
            "thinking_enabled": settings.ai_interpretation_thinking_enabled,
            "visual_enabled": settings.ai_interpretation_visual_enabled,
            "model_supports_vision": settings.ai_interpretation_model_supports_vision,
            "model_supports_structured_output": settings.ai_interpretation_model_supports_structured_output,
        },
        prompt_version=PROMPT_POLICY_VERSION,
        output_schema_version=INTERPRETATION_OUTPUT_SCHEMA,
        knowledge_base_version=registry.version,
        knowledge_ids=[f"{item.knowledge_id}@{item.version}" for item in projected.knowledge],
        execution_mode="visual" if settings.ai_interpretation_visual_configured and projected.evidence else "text",
        evidence_manifest=[item.model_dump(mode="json") for item in projected.evidence],
        evidence_exclusions=[item.model_dump(mode="json") for item in projected.evidence_exclusions],
        status="pending",
        validation_result={},
        usage={},
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record, False


def _mark_failed(
    db: Session,
    record: ReportInterpretation,
    *,
    code: str,
    message: str,
    retryable: bool,
    validation_result: dict[str, Any] | None = None,
    usage: dict[str, Any] | None = None,
) -> None:
    record.status = "failed"
    record.content = None
    record.error_code = code
    record.error_message = message[:4000]
    record.retryable = retryable
    record.validation_result = validation_result or {
        "valid": False,
        "guardrail_rejected": code in GUARDRAIL_ERROR_CODES,
        "error_code": code,
    }
    record.usage = usage or record.usage or {}
    record.completed_at = _utcnow()
    db.add(record)
    db.commit()


def execute_interpretation(
    interpretation_id: int,
    *,
    db: Session | None = None,
    settings: Settings | None = None,
    provider: InterpretationProvider | None = None,
    registry: KnowledgeRegistry | None = None,
) -> ReportInterpretation | None:
    own_session = db is None
    db = db or SessionLocal()
    settings = settings or get_settings()
    timer = GenerationTimer()
    try:
        record = db.get(ReportInterpretation, interpretation_id)
        if record is None:
            return None
        if record.status == "ready":
            return record
        report = db.get(ReportMetadata, record.report_metadata_id)
        if report is None:
            _mark_failed(db, record, code="base_report_missing", message="基础报告不存在", retryable=False)
            return record

        projected, registry, current_signature, current_input_hash = prepare_input(
            report.report_data or {}, settings, registry
        )
        if (
            record.base_report_generation_signature != _base_signature(report.report_data or {})
            or record.generation_signature != current_signature
            or record.input_hash != current_input_hash
        ):
            record.status = "stale"
            record.completed_at = _utcnow()
            db.add(record)
            db.commit()
            return record

        record.status = "generating"
        record.started_at = _utcnow()
        record.error_code = None
        record.error_message = None
        db.add(record)
        db.commit()

        provider = provider or build_provider(settings)
        evidence_bundle = build_evidence_bundle(report.report_data or {}, projected, settings)
        visual_mode = bool(settings.ai_interpretation_visual_configured and evidence_bundle.image_data_urls)
        response = provider.generate(ProviderRequest(
            policy=SYSTEM_POLICY,
            input=projected,
            output_schema=InterpretationOutput.model_json_schema(),
            evidence_images=evidence_bundle.image_data_urls if visual_mode else {},
            visual_mode=visual_mode,
        ))
        output = parse_output(response.output)
        completed_refs = complete_numeric_fact_refs(output, projected)
        validation_result = success_validation_metrics(
            output,
            projected,
            validate_output(output, projected),
        )
        validation_result["completed_numeric_fact_refs"] = completed_refs
        record.status = "ready"
        record.content = output.model_dump(mode="json")
        record.validation_result = validation_result
        record.usage = usage_metrics(
            response.usage,
            settings=settings,
            latency_ms=timer.elapsed_ms,
            retry_count=int(response.usage.get("retry_count", 0)),
        )
        record.error_code = None
        record.error_message = None
        record.retryable = False
        record.execution_mode = "visual" if visual_mode else "text"
        record.evidence_manifest = [item.model_dump(mode="json") for item in projected.evidence]
        record.evidence_exclusions = [item.model_dump(mode="json") for item in projected.evidence_exclusions]
        record.completed_at = _utcnow()
        db.add(record)
        db.commit()
        db.refresh(record)
        return record
    except ProviderError as exc:
        if "record" in locals() and record is not None:
            _mark_failed(
                db,
                record,
                code=exc.code,
                message=exc.message,
                retryable=exc.retryable,
                usage=usage_metrics(
                    {}, settings=settings, latency_ms=timer.elapsed_ms, retry_count=exc.retry_count
                ),
            )
            return record
        raise
    except InterpretationValidationError as exc:
        if "record" in locals() and record is not None:
            _mark_failed(
                db,
                record,
                code=exc.code,
                message=exc.message,
                retryable=False,
                usage=usage_metrics({}, settings=settings, latency_ms=timer.elapsed_ms),
            )
            return record
        raise
    except Exception as exc:
        if "record" in locals() and record is not None:
            _mark_failed(
                db,
                record,
                code="interpretation_internal_error",
                message=str(exc),
                retryable=True,
                usage=usage_metrics({}, settings=settings, latency_ms=timer.elapsed_ms),
            )
            return record
        raise
    finally:
        if own_session:
            db.close()


def _trace(record: ReportInterpretation) -> InterpretationTrace:
    return InterpretationTrace(
        generation_signature=record.generation_signature,
        base_report_generation_signature=record.base_report_generation_signature,
        provider=record.provider,
        model=record.model,
        prompt_version=record.prompt_version,
        output_schema_version=record.output_schema_version,
        knowledge_base_version=record.knowledge_base_version,
        knowledge_ids=list(record.knowledge_ids or []),
        execution_mode=getattr(record, "execution_mode", "text") or "text",
        evidence_ids=[item.get("evidence_id") for item in (getattr(record, "evidence_manifest", None) or []) if item.get("evidence_id")],
        evidence_exclusion_reasons=sorted({item.get("reason") for item in (getattr(record, "evidence_exclusions", None) or []) if item.get("reason")}),
        generated_at=record.completed_at,
    )


def resolve_interpretation_envelope(
    db: Session,
    report: ReportMetadata,
    *,
    settings: Settings | None = None,
) -> InterpretationEnvelope:
    settings = settings or get_settings()
    base_signature = _base_signature(report.report_data or {})
    records = db.scalars(
        select(ReportInterpretation)
        .where(ReportInterpretation.report_metadata_id == report.id)
        .order_by(ReportInterpretation.created_at.desc(), ReportInterpretation.id.desc())
    ).all()
    current = [item for item in records if item.base_report_generation_signature == base_signature]
    ready = next((item for item in current if item.status == "ready"), None)
    if ready is not None and ready.content:
        try:
            content = InterpretationOutput.model_validate(ready.content)
        except Exception:
            return InterpretationEnvelope(
                status="failed",
                error=InterpretationError(code="persisted_output_invalid", message="已保存的 AI 解读无效"),
                can_regenerate=settings.ai_interpretation_configured,
            )
        return InterpretationEnvelope(status="ready", content=content, trace=_trace(ready), can_regenerate=True)

    active = next((item for item in current if item.status in ("generating", "pending")), None)
    if active is not None:
        return InterpretationEnvelope(status=active.status, trace=_trace(active), can_regenerate=False)
    failed = next((item for item in current if item.status == "failed"), None)
    if failed is not None:
        return InterpretationEnvelope(
            status="failed",
            trace=_trace(failed),
            error=InterpretationError(
                code=failed.error_code or "interpretation_failed",
                message=failed.error_message or "AI 解读生成失败",
                retryable=failed.retryable,
            ),
            can_regenerate=settings.ai_interpretation_configured,
        )
    if records:
        return InterpretationEnvelope(status="stale", trace=_trace(records[0]), can_regenerate=settings.ai_interpretation_configured)
    if not settings.ai_interpretation_configured:
        return InterpretationEnvelope(status="not_configured", can_regenerate=False)
    return InterpretationEnvelope(status="pending", can_regenerate=True)


def recover_stale_jobs(
    db: Session,
    schedule: Callable[[int], None],
    *,
    settings: Settings | None = None,
) -> int:
    settings = settings or get_settings()
    if not settings.ai_interpretation_configured:
        return 0
    cutoff = _utcnow() - timedelta(seconds=settings.ai_interpretation_stale_after_seconds)
    records = db.scalars(
        select(ReportInterpretation).where(
            (ReportInterpretation.status == "pending")
            | (
                (ReportInterpretation.status == "generating")
                & (ReportInterpretation.started_at < cutoff)
            )
        )
    ).all()
    for record in records:
        record.status = "pending"
        db.add(record)
    db.commit()
    for record in records:
        schedule(record.id)
    return len(records)
