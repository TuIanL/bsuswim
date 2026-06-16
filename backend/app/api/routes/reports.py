from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models import AnalysisTask, ReportMetadata, TrainingSession, User
from app.schemas import ReportData, ReportGenerate
from app.services.report_builder import build_report_data

router = APIRouter()


@router.post("/generate", response_model=ReportData, status_code=status.HTTP_201_CREATED)
def generate_report(
    payload: ReportGenerate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReportData:
    session = _get_owned_session(db, payload.session_id, current_user)
    task = db.scalar(
        select(AnalysisTask)
        .where(AnalysisTask.session_id == session.id)
        .options(
            joinedload(AnalysisTask.result),
            joinedload(AnalysisTask.session).joinedload(TrainingSession.athlete),
        )
        .order_by(AnalysisTask.updated_at.desc())
    )
    if not task or not task.result:
        raise HTTPException(status_code=404, detail="分析结果尚未生成")

    report_data = build_report_data(task, task.result)
    report = db.scalar(select(ReportMetadata).where(ReportMetadata.session_id == session.id))
    if report:
        report.task_id = task.id
        report.source = "model_service"
        report.report_data = report_data
    else:
        report = ReportMetadata(session_id=session.id, task_id=task.id, source="model_service", report_data=report_data)

    db.add(report)
    db.commit()
    db.refresh(report)
    return _read_report(report)


@router.get("/{session_id}", response_model=ReportData)
def get_report(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReportData:
    _get_owned_session(db, session_id, current_user)
    report = db.scalar(select(ReportMetadata).where(ReportMetadata.session_id == session_id))
    if not report:
        raise HTTPException(status_code=404, detail="报告尚未生成")
    return _read_report(report)


def _get_owned_session(db: Session, session_id: int, current_user: User) -> TrainingSession:
    session = db.get(TrainingSession, session_id)
    if not session or session.coach_id != current_user.id:
        raise HTTPException(status_code=404, detail="训练记录不存在")
    return session


def _read_report(report: ReportMetadata) -> ReportData:
    return ReportData(
        session_id=report.session_id,
        task_id=report.task_id,
        source=report.source,
        generated_at=report.generated_at,
        report=report.report_data,
    )
