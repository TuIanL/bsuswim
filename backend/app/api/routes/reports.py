from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models import AnalysisResult, AnalysisTask, ReportMetadata, TrainingSession, User
from app.schemas import ReportData, ReportGenerate
from app.services.report_builder import build_report_data, build_swim_report_data, merge_into_existing
from app.services.reporting.resolver import resolve_annotation_metric_for_result

router = APIRouter()


def _mark_pdf_stale_on_data_update(db: Session, session_id: int) -> None:
    db.execute(
        update(ReportMetadata)
        .where(
            ReportMetadata.session_id == session_id,
            ReportMetadata.pdf_status == "exported",
        )
        .values(pdf_status="stale")
    )
    db.commit()


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
        report.source = "model_service_mock"
        report.report_data = report_data
        if report.pdf_status == "exported":
            report.pdf_status = "stale"
    else:
        report = ReportMetadata(session_id=session.id, task_id=task.id, source="model_service_mock", report_data=report_data)

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


@router.post("/from-analysis-results/{analysis_result_id}/swim", status_code=status.HTTP_200_OK)
def build_swim_report(
    analysis_result_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    result = db.get(AnalysisResult, analysis_result_id)
    if not result:
        raise HTTPException(status_code=404, detail="分析结果不存在")

    annotation_metric = resolve_annotation_metric_for_result(db, result)
    if not annotation_metric:
        raise HTTPException(
            status_code=422,
            detail="annotation_metrics 未就绪，请先完成指标计算",
        )

    diagnostics = result.diagnostics or []
    is_partial = len(diagnostics) == 0

    report_data = build_swim_report_data(result, annotation_metric, diagnostics)
    if is_partial:
        report_data["status"] = "partial"
        report_data.setdefault("warnings", []).append("diagnostics_empty")

    task = result.task
    if not task:
        raise HTTPException(status_code=422, detail="分析结果未关联分析任务")

    report = db.scalar(select(ReportMetadata).where(ReportMetadata.session_id == task.session_id))
    if report:
        report.report_data = merge_into_existing(report.report_data or {}, report_data)
        report.source = "kinovea_assisted"
        if report.pdf_status == "exported":
            report.pdf_status = "stale"
    else:
        report = ReportMetadata(
            session_id=task.session_id,
            task_id=task.id,
            source="kinovea_assisted",
            report_data=report_data,
        )
    db.add(report)
    db.commit()
    db.refresh(report)

    return {
        "report_id": report.id,
        "report_data_id": report.id,
        "status": "partial" if is_partial else "generated",
        "section_count": len(report_data.get("sections", [])),
        "warnings": report_data.get("warnings", []),
    }



