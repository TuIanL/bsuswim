from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import ReportMetadata
from app.schemas import ReportData

router = APIRouter()


@router.get("/{task_id}", response_model=ReportData)
def get_report(task_id: int, db: Session = Depends(get_db)) -> ReportData:
    report = db.scalar(select(ReportMetadata).where(ReportMetadata.task_id == task_id))
    if not report:
        raise HTTPException(status_code=404, detail="报告尚未生成")
    return ReportData(
        task_id=task_id,
        source=report.source,
        generated_at=report.generated_at,
        report=report.report_data,
    )
