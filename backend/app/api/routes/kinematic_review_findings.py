"""二维运动学复核发现 API 端点。

挂载在 metrics 路由下，完整路径：
    POST /api/v1/annotation-metrics/{id}/review-findings/generate
    GET  /api/v1/annotation-metrics/{id}/review-findings

错误码（design §8）：
    404 metric_unavailable / review_findings_not_generated
    409 metric_revision_stale
    422 unsupported_metric_schema / invalid_metric_payload / invalid_rule_set / rule_output_kind_mismatch
    500 review_findings_generation_failed
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models import User
from app.schemas.kinematic_review_finding import (
    ReviewFindingsGenerateResponse,
    ReviewFindingsReadResponse,
)
from app.services.diagnostics.review_findings.generation_service import (
    ReviewFindingsGenerationError,
    generate_review_findings,
    get_current_review_findings,
)

router = APIRouter()


@router.post(
    "/annotation-metrics/{annotation_metric_id}/review-findings/generate",
    response_model=ReviewFindingsGenerateResponse,
    status_code=status.HTTP_200_OK,
)
def generate_review_findings_endpoint(
    annotation_metric_id: int,
    rule_set: str = Query(default="side_2d_kinematics_v1"),
    force: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """生成指定 AnnotationMetric 的待复核发现。"""
    try:
        finding_set, created = generate_review_findings(
            db, annotation_metric_id, current_user, rule_set=rule_set, force=force
        )
    except ReviewFindingsGenerationError as exc:
        raise HTTPException(status_code=exc.http_status, detail={"code": exc.code, "message": exc.message})
    return ReviewFindingsGenerateResponse(
        finding_set_id=finding_set.id,
        annotation_metric_id=annotation_metric_id,
        rule_set=finding_set.rule_set,
        status=finding_set.status,
        finding_count=finding_set.summary.get("review_required_count", 0) if isinstance(finding_set.summary, dict) else 0,
        created=created,
    )


@router.get(
    "/annotation-metrics/{annotation_metric_id}/review-findings",
    response_model=ReviewFindingsReadResponse,
    status_code=status.HTTP_200_OK,
)
def get_review_findings_endpoint(
    annotation_metric_id: int,
    rule_set: str = Query(default="side_2d_kinematics_v1"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """读取当前规则/版本对应的待复核发现（按 expected signature，不取最新行）。"""
    try:
        finding_set = get_current_review_findings(db, annotation_metric_id, current_user, rule_set=rule_set)
    except ReviewFindingsGenerationError as exc:
        raise HTTPException(status_code=exc.http_status, detail={"code": exc.code, "message": exc.message})
    return ReviewFindingsReadResponse(
        id=finding_set.id,
        annotation_metric_id=finding_set.annotation_metric_id,
        normalized_annotation_id=finding_set.normalized_annotation_id,
        session_video_id=finding_set.session_video_id,
        schema_version=finding_set.schema_version,
        rule_set=finding_set.rule_set,
        rule_version=finding_set.rule_version,
        engine_version=finding_set.engine_version,
        threshold_basis=finding_set.threshold_basis,
        source_annotation_revision=finding_set.source_annotation_revision,
        generation_signature=finding_set.generation_signature,
        status=finding_set.status,
        findings=finding_set.findings if isinstance(finding_set.findings, list) else [],
        summary=finding_set.summary if isinstance(finding_set.summary, dict) else {},
        skipped_rules=finding_set.skipped_rules if isinstance(finding_set.skipped_rules, list) else [],
        warnings=finding_set.warnings if isinstance(finding_set.warnings, list) else [],
        created_at=finding_set.created_at,
    )
