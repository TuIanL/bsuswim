from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models import ReportMetadata, User
from app.repositories.training_session_repository import require_owned_session
from app.schemas.report_interpretation import (
    InterpretationEnvelope,
    InterpretationGenerateRequest,
    InterpretationGenerateResponse,
)
from app.services.report_interpretation import (
    create_or_reuse_interpretation,
    resolve_interpretation_envelope,
)
from app.services.report_interpretation.provider import ProviderError
from app.services.report_interpretation.scheduler import schedule_interpretation

router = APIRouter(prefix="/sessions/{session_id}/report/interpretation")


def _owned_report(db: Session, session_id: int, user_id: int) -> ReportMetadata:
    require_owned_session(db, session_id=session_id, user_id=user_id)
    report = db.scalar(select(ReportMetadata).where(ReportMetadata.session_id == session_id))
    if report is None:
        raise HTTPException(status_code=404, detail={"code": "report_not_found", "message": "报告不存在"})
    return report


@router.get("", response_model=InterpretationEnvelope)
def get_interpretation(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InterpretationEnvelope:
    report = _owned_report(db, session_id, current_user.id)
    return resolve_interpretation_envelope(db, report)


@router.post("/generate", response_model=InterpretationGenerateResponse, status_code=status.HTTP_202_ACCEPTED)
def generate_interpretation(
    session_id: int,
    payload: InterpretationGenerateRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InterpretationGenerateResponse:
    report = _owned_report(db, session_id, current_user.id)
    try:
        record, reused = create_or_reuse_interpretation(
            db,
            report,
            requested_by_user_id=current_user.id,
            force=(payload or InterpretationGenerateRequest()).force,
        )
    except ProviderError as exc:
        code = (
            429
            if exc.code == "interpretation_rate_limited"
            else 409
            if exc.code == "interpretation_queue_busy"
            else 422
        )
        raise HTTPException(
            status_code=code,
            detail={"code": exc.code, "message": exc.message, "retryable": exc.retryable},
        ) from exc
    if record is None:
        return InterpretationGenerateResponse(status="not_configured")
    if not reused:
        schedule_interpretation(record.id)
    return InterpretationGenerateResponse(
        interpretation_id=record.id,
        status=record.status,
        generation_signature=record.generation_signature,
        reused=reused,
    )
