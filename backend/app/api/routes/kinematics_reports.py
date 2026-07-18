"""API route for five-page kinematics report assembly."""

from fastapi import APIRouter, Depends, Path, status as http_status

from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.kinematics_report import FivePageKinematicsReport

router = APIRouter()


@router.post(
    "/annotation-metrics/{annotation_metric_id}/reports/five-page/assemble",
    response_model=FivePageKinematicsReport,
    summary="装配五页二维运动学报告",
    status_code=http_status.HTTP_200_OK,
)
def assemble_five_page_report(
    annotation_metric_id: int = Path(..., description="AnnotationMetric ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FivePageKinematicsReport:
    """将当前有效的 AnnotationMetric、KinematicArtifactSet 和 KinematicReviewFindingSet
    装配为固定五页的 swim-report.v1。不写入 ReportMetadata。
    """
    from app.services.reporting.kinematics_report.assembly_service import assemble_five_page_kinematics_report

    report = assemble_five_page_kinematics_report(db, annotation_metric_id, current_user)
    return report
