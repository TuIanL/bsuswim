from app.core.config import get_settings


def build_session_report_pdf_url(session_id: int) -> str:
    settings = get_settings()
    return (
        f"{settings.api_prefix}"
        f"/sessions/{session_id}/report/pdf"
    )
