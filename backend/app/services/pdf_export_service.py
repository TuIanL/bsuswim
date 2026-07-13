from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import ReportMetadata
from app.services.playwright_renderer import render_pdf_from_url
from app.services.print_token_service import generate_print_token
from app.services.storage import StorageService


class PdfExportService:
    def __init__(self, db: Session, storage: StorageService):
        self.db = db
        self.storage = storage

    async def export_report_pdf(
        self,
        report_id: int,
        session_id: int,
        user_id: int,
    ) -> dict:
        report = self.db.get(ReportMetadata, report_id)
        if not report:
            raise ValueError("Report not found")

        settings = get_settings()
        frontend_url = settings.pdf_render_base_url or settings.frontend_base_url or "http://localhost:5173"

        token = generate_print_token(
            report_id=report.id,
            session_id=session_id,
            user_id=user_id,
        )

        print_url = f"{frontend_url}/reports/{session_id}/print?token={token}"

        pdf_bytes = await render_pdf_from_url(print_url)

        next_version = (report.pdf_version or 0) + 1
        relative_path = f"reports/{report.id}/report_v{next_version}.pdf"

        result = self.storage.save_bytes(
            pdf_bytes,
            relative_path=relative_path,
            content_type="application/pdf",
        )

        report.pdf_path = result["relative_path"]
        report.pdf_status = "exported"
        report.pdf_exported_at = datetime.now(timezone.utc)
        report.pdf_version = next_version
        report.pdf_error = None
        self.db.commit()

        return {
            "report_id": report.id,
            "pdf_status": "exported",
            "pdf_url": f"/api/sessions/{session_id}/report/pdf",
            "pdf_exported_at": report.pdf_exported_at.isoformat(),
        }
