from typing import NoReturn

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models import ReportMetadata, User
from app.repositories.training_session_repository import require_owned_session
from app.services.pdf_export_service import PdfExportService
from app.services.print_token_service import validate_print_token
from app.services.reporting.pdf_url import build_session_report_pdf_url
from app.services.storage import StorageService

public_router = APIRouter(tags=["report-exports"])
internal_router = APIRouter(
    prefix="/internal",
    tags=["internal-report-exports"],
    include_in_schema=False,
)


def _raise_pdf_state_error(
    report: ReportMetadata,
    session_id: int,
) -> NoReturn:
    if report.pdf_status == "exporting":
        raise HTTPException(
            status_code=409,
            detail={
                "code": "pdf_export_in_progress",
                "message": "PDF 正在生成",
                "pdf_status": report.pdf_status,
                "status_url": (
                    f"/api/v1/sessions/{session_id}"
                    "/report/export/pdf/status"
                ),
            },
        )

    if report.pdf_status == "export_failed":
        raise HTTPException(
            status_code=409,
            detail={
                "code": "pdf_export_failed",
                "message": "PDF 导出失败，请重新生成",
                "pdf_status": report.pdf_status,
                "export_url": (
                    f"/api/v1/sessions/{session_id}"
                    "/report/export/pdf"
                ),
            },
        )

    raise HTTPException(
        status_code=404,
        detail={
            "code": "pdf_not_exported",
            "message": "PDF 尚未生成",
            "pdf_status": report.pdf_status or "not_exported",
            "export_url": (
                f"/api/v1/sessions/{session_id}"
                "/report/export/pdf"
            ),
        },
    )


def _resolve_current_owned_report(
    db: Session,
    *,
    session_id: int,
    user_id: int,
) -> ReportMetadata:
    require_owned_session(db, session_id=session_id, user_id=user_id)

    report = db.scalar(
        select(ReportMetadata).where(
            ReportMetadata.session_id == session_id
        )
    )
    if report is None:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "report_not_found",
                "message": "当前训练记录尚无报告",
            },
        )
    return report


@public_router.post(
    "/sessions/{session_id}/report/export/pdf",
    status_code=status.HTTP_200_OK,
)
async def export_session_report_pdf(
    session_id: int,
    payload: dict | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    require_owned_session(db, session_id=session_id, user_id=current_user.id)

    report = db.scalar(
        select(ReportMetadata).where(
            ReportMetadata.session_id == session_id
        )
    )
    if not report:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "report_not_found",
                "message": "报告不存在",
            },
        )

    if report.pdf_status == "exporting":
        raise HTTPException(
            status_code=409,
            detail={
                "code": "pdf_export_in_progress",
                "message": "PDF is already exporting",
            },
        )

    force = (payload or {}).get("force", False)
    if report.pdf_status == "exported" and report.pdf_path and not force:
        return {
            "report_id": report.id,
            "report_data_id": report.id,
            "pdf_status": "exported",
            "pdf_url": build_session_report_pdf_url(session_id),
            "pdf_exported_at": report.pdf_exported_at.isoformat() if report.pdf_exported_at else None,
        }

    stmt = (
        update(ReportMetadata)
        .where(ReportMetadata.id == report.id, ReportMetadata.pdf_status != "exporting")
        .values(pdf_status="exporting", pdf_error=None)
    )
    result = db.execute(stmt)
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "pdf_export_in_progress",
                "message": "PDF is already exporting",
            },
        )

    storage = StorageService()
    export_service = PdfExportService(db=db, storage=storage)
    try:
        result_data = await export_service.export_report_pdf(
            report_id=report.id,
            session_id=session_id,
            user_id=current_user.id,
        )
        return result_data
    except Exception as exc:
        failed_report = db.get(ReportMetadata, report.id)
        if failed_report:
            failed_report.pdf_status = "export_failed"
            failed_report.pdf_error = str(exc)
            db.commit()
        raise HTTPException(
            status_code=500,
            detail={
                "code": "pdf_export_failed",
                "message": f"PDF 导出失败: {exc}",
            },
        )


@public_router.get("/sessions/{session_id}/report/pdf")
def download_session_report_pdf(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    report = _resolve_current_owned_report(
        db, session_id=session_id, user_id=current_user.id
    )

    if report.pdf_status == "exported" and not report.pdf_path:
        report.pdf_status = "export_failed"
        report.pdf_error = "pdf_artifact_missing"
        db.commit()
        raise HTTPException(
            status_code=500,
            detail={
                "code": "pdf_artifact_missing",
                "message": "PDF 文件状态异常，请重新导出",
                "pdf_status": "export_failed",
            },
        )

    if report.pdf_status != "exported" or not report.pdf_path:
        _raise_pdf_state_error(report, session_id)

    storage = StorageService()
    pdf_abs_path = storage.resolve_path(report.pdf_path)

    if not pdf_abs_path.is_file():
        report.pdf_status = "export_failed"
        report.pdf_error = "pdf_artifact_missing"
        db.commit()

        raise HTTPException(
            status_code=500,
            detail={
                "code": "pdf_artifact_missing",
                "message": "PDF 文件状态异常，请重新导出",
                "pdf_status": "export_failed",
            },
        )

    return FileResponse(
        path=str(pdf_abs_path),
        media_type="application/pdf",
        filename=f"游泳技术报告_{session_id}.pdf",
    )


@public_router.get("/sessions/{session_id}/report/export/pdf/status")
def get_session_report_pdf_status(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    report = _resolve_current_owned_report(
        db, session_id=session_id, user_id=current_user.id
    )

    return {
        "report_id": report.id,
        "report_data_id": report.id,
        "pdf_status": report.pdf_status,
        "pdf_exported_at": report.pdf_exported_at.isoformat() if report.pdf_exported_at else None,
        "pdf_error": report.pdf_error,
    }


@internal_router.get("/sessions/{session_id}/report/print-data")
def get_print_data(
    session_id: int,
    token: str = Query(...),
    db: Session = Depends(get_db),
) -> dict:
    claims = validate_print_token(
        token,
        expected_session_id=session_id,
        expected_purpose="pdf_export",
    )
    if claims is None:
        raise HTTPException(
            status_code=401,
            detail={
                "code": "invalid_print_token",
                "message": "打印凭证无效或已过期",
            },
        )

    report = db.get(ReportMetadata, claims["report_id"])
    if not report or report.session_id != session_id or not report.report_data:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "report_not_found",
                "message": "打印报告不存在",
            },
        )

    from app.core.config import get_settings
    settings = get_settings()
    report_data = dict(report.report_data)

    sections = report_data.get("sections", []) or []
    for section in sections:
        for asset in section.get("assets", []) or []:
            url = asset.get("url") or asset.get("image_url")
            if url and url.startswith("/"):
                asset["absolute_url"] = f"{settings.backend_public_base_url}{url}"
            else:
                asset["absolute_url"] = url or ""

    return {
        "report_data": report_data,
    }
