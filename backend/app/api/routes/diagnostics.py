"""诊断 API 端点。

挂载在 analysis 路由下（前缀 /analysis），完整路径：
    POST /api/v1/analysis/analysis-results/{id}/diagnostics/run
    GET  /api/v1/analysis/analysis-results/{id}/diagnostics

错误码（设计 §7.3）：
    404：analysis_result 不存在
    422：存在但解析不到 side AnnotationMetric（不静默空跑）
    409：已有 diagnostics 且 overwrite=false
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models import AnalysisResult, User
from app.schemas.diagnostics import (
    DiagnosticsMeta,
    DiagnosticsReadResponse,
    DiagnosticsRunResponse,
)
from app.services.diagnostics.bridge import (
    AnnotationQualityBlockedError,
    DiagnosticsBridgeError,
    run_diagnostics_for_analysis_result,
)
from app.services.diagnostics.models import DiagnosticItem, DiagnosticsSummary

router = APIRouter()


class DiagnosticsRunRequest(BaseModel):
    rule_set: str = "side_freestyle_v1"
    overwrite: bool = True


def _meta_from_raw(result: AnalysisResult) -> DiagnosticsMeta | None:
    meta = (result.raw_result or {}).get("diagnostics_meta")
    if not meta:
        return None
    return DiagnosticsMeta(**meta)


@router.post(
    "/analysis-results/{analysis_result_id}/diagnostics/run",
    response_model=DiagnosticsRunResponse,
    status_code=status.HTTP_200_OK,
)
def run_diagnostics(
    analysis_result_id: int,
    payload: DiagnosticsRunRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DiagnosticsRunResponse:
    result = db.get(AnalysisResult, analysis_result_id)
    if result is None:
        raise HTTPException(status_code=404, detail="分析结果不存在")
    _ensure_owned(db, result, current_user)

    try:
        output = run_diagnostics_for_analysis_result(
            db,
            analysis_result_id,
            rule_set=payload.rule_set,
            overwrite=payload.overwrite,
        )
    except DiagnosticsBridgeError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except AnnotationQualityBlockedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": {
                    "code": "ANNOTATION_QUALITY_BLOCKED",
                    "message": str(exc),
                    "details": exc.quality,
                }
            },
        )

    # 引擎已写回 result.raw_result["diagnostics_meta"]，直接读取
    meta = _meta_from_raw(result)
    return DiagnosticsRunResponse(
        analysis_result_id=analysis_result_id,
        rule_set=payload.rule_set,
        diagnostics_count=len(output.diagnostics),
        summary=output.summary,
        diagnostics=output.diagnostics,
        diagnostics_meta=meta
        or DiagnosticsMeta(
            rule_set=payload.rule_set,
            rule_version="",
            engine_version=output.engine_version
            if hasattr(output, "engine_version")
            else "",
            matched_rule_ids=output.matched_rule_ids,
            skipped_rule_ids=output.skipped_rules,
            partial_evaluation_warnings=output.partial_evaluation_warnings,
        ),
    )


@router.get(
    "/analysis-results/{analysis_result_id}/diagnostics",
    response_model=DiagnosticsReadResponse,
)
def get_diagnostics(
    analysis_result_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DiagnosticsReadResponse:
    result = db.get(AnalysisResult, analysis_result_id)
    if result is None:
        raise HTTPException(status_code=404, detail="分析结果不存在")
    _ensure_owned(db, result, current_user)

    diagnostics = [DiagnosticItem(**d) for d in (result.diagnostics or [])]
    meta = _meta_from_raw(result)

    return DiagnosticsReadResponse(
        analysis_result_id=analysis_result_id,
        rule_set=meta.rule_set if meta else None,
        diagnostics=diagnostics,
        summary=DiagnosticsSummary(),
        diagnostics_meta=meta,
    )


def _ensure_owned(db: Session, result: AnalysisResult, user: User) -> None:
    """仅允许教练访问自己训练记录下的分析结果。"""
    task = result.task
    if task is None or task.session is None or task.session.coach_id != user.id:
        raise HTTPException(status_code=404, detail="分析结果不存在")
