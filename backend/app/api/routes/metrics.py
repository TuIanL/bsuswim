from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models import User
from app.repositories.normalized_annotation_repository import get_with_ownership_check
from app.schemas.metrics import AnnotationMetricRead, CalculateMetricsResponse
from app.services.metrics_service import (
    calculate_and_persist,
    get_latest_metric,
    get_metric_by_id,
)

router = APIRouter()


@router.post(
    "/normalized-annotations/{normalized_annotation_id}/calculate-metrics",
    response_model=CalculateMetricsResponse,
)
def calculate_metrics_endpoint(
    normalized_annotation_id: int,
    persist: bool = Query(default=False, description="true 时写入 annotation_metrics"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """计算 side-view metrics。persist=true 写入 annotation_metrics 并返回 id。"""
    # 权限校验：normalized_annotation → session_video → training_session → coach
    ann = get_with_ownership_check(db, normalized_annotation_id, current_user.id)
    try:
        metrics, metric_id = calculate_and_persist(
            db,
            normalized_annotation_id,
            persist=persist,
            current_user_id=current_user.id,
        )
    except ValueError as exc:
        # 非 side 视角：422；其余视为 400
        code = "unsupported_camera_view" if "camera_view" in str(exc) else "calculation_error"
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY if code == "unsupported_camera_view" else status.HTTP_400_BAD_REQUEST,
            detail={"code": code, "message": str(exc)},
        )

    return CalculateMetricsResponse(
        annotation_metric_id=metric_id,
        normalized_annotation_id=normalized_annotation_id,
        schema_version=metrics.get("schema_version", "swim-side-metrics.v1"),
        camera_view=metrics.get("camera_view", "side"),
        metrics=metrics,
        quality=metrics.get("quality", {}),
    )


@router.get(
    "/normalized-annotations/{normalized_annotation_id}/metrics",
    response_model=AnnotationMetricRead,
)
def get_metrics_for_annotation(
    normalized_annotation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """读取某标注最新一条 annotation_metrics。"""
    get_with_ownership_check(db, normalized_annotation_id, current_user.id)
    record = get_latest_metric(db, normalized_annotation_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="尚未计算 metrics")
    return record


@router.get(
    "/annotation-metrics/{annotation_metric_id}",
    response_model=AnnotationMetricRead,
)
def get_annotation_metric(
    annotation_metric_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """按 id 读取 annotation_metrics（供 Change #5 诊断模块直接引用）。"""
    record = get_metric_by_id(db, annotation_metric_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="annotation_metrics 不存在")
    # 轻量权限：校验其归属标注的 owner
    get_with_ownership_check(db, record.normalized_annotation_id, current_user.id)
    return record
