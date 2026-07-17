from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models import User
from app.repositories.normalized_annotation_repository import get_with_ownership_check
from app.schemas.metrics import (
    AnnotationMetricRead,
    CALCULATOR_SIDE_VIEW_METRICS,
    CalculateMetricsResponse,
)
from app.services.metrics.kinematics.registry import (
    has_calculator,
    register_builtin_calculators,
)
from app.services.metrics_service import (
    calculate_and_persist,
    compute_revision_status,
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
    calculator: str = Query(
        default=CALCULATOR_SIDE_VIEW_METRICS,
        description="计算器名字：side_view_metrics | side_2d_kinematics",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """计算指定 calculator 的 metrics。persist=true 写入 annotation_metrics 并返回 id。"""
    register_builtin_calculators()
    if not has_calculator(calculator):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "unsupported_metric_calculator", "message": f"未知计算器: {calculator}"},
        )

    get_with_ownership_check(db, normalized_annotation_id, current_user.id)
    try:
        metrics, metric_id = calculate_and_persist(
            db,
            normalized_annotation_id,
            persist=persist,
            current_user_id=current_user.id,
            calculator=calculator,
        )
    except ValueError as exc:
        msg = str(exc)
        if "unsupported calculator" in msg:
            code = "unsupported_metric_calculator"
        elif "camera_view" in msg:
            code = "unsupported_camera_view"
        elif "no usable skeleton frames" in msg:
            code = "no_usable_skeleton_frames"
        else:
            code = "calculation_error"
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": code, "message": msg},
        )

    return CalculateMetricsResponse(
        annotation_metric_id=metric_id,
        normalized_annotation_id=normalized_annotation_id,
        schema_version=metrics.get("schema_version", "swim-side-metrics.v1"),
        camera_view=metrics.get("camera_view", "side"),
        calculator=metrics.get("calculator", CALCULATOR_SIDE_VIEW_METRICS),
        calculator_version=metrics.get("calculator_version", "0.1.0"),
        source_revision=metrics.get("source", {}).get("revision"),
        revision_status=metrics.get("source", {}).get("revision_status"),
        metrics=metrics,
        quality=metrics.get("quality", {}),
    )


@router.get(
    "/normalized-annotations/{normalized_annotation_id}/metrics",
    response_model=AnnotationMetricRead,
)
def get_metrics_for_annotation(
    normalized_annotation_id: int,
    calculator: str = Query(default=CALCULATOR_SIDE_VIEW_METRICS),
    calculator_version: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """读取某标注最新一条 annotation_metrics（按 calculator / calculator_version 过滤）。"""
    register_builtin_calculators()
    if not has_calculator(calculator):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "unsupported_metric_calculator", "message": f"未知计算器: {calculator}"},
        )

    ann = get_with_ownership_check(db, normalized_annotation_id, current_user.id)
    stmt_calc = calculator
    record = get_latest_metric(db, normalized_annotation_id, calculator=stmt_calc)
    if calculator_version and record and record.calculator_version != calculator_version:
        # 该版本无记录：回退为 None → 404
        record = None
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="尚未计算 metrics")

    revision_status = compute_revision_status(record, ann)
    read = AnnotationMetricRead.model_validate(record)
    read.revision_status = revision_status
    return read


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
    ann = get_with_ownership_check(db, record.normalized_annotation_id, current_user.id)
    revision_status = compute_revision_status(record, ann)
    read = AnnotationMetricRead.model_validate(record)
    read.revision_status = revision_status
    return read
