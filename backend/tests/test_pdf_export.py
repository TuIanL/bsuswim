"""PDF 导出服务单测。

- Print token / storage save_bytes / resolver：纯单元测试，无 DB。
- Mock API 测试：不依赖真实 DB，mock 掉 service 层。
- Integration 标记（@pytest.mark.integration）：需 PostgreSQL + Playwright。
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.services.print_token_service import (
    consume_print_token,
    generate_print_token,
    validate_print_token,
)
from app.services.storage import StorageService


# ── 11.6 Print-token 基础功能 ──


def test_generate_and_validate_token():
    token = generate_print_token(
        report_id=1,
        session_id=101,
        user_id=42,
    )
    assert len(token) > 16

    record = validate_print_token(
        token,
        expected_session_id=101,
        expected_purpose="pdf_export",
    )
    assert record is not None
    assert record["report_id"] == 1
    assert record["session_id"] == 101
    assert record["user_id"] == 42
    assert record["purpose"] == "pdf_export"
    assert record["read_count"] >= 1


def test_validate_wrong_session_returns_none():
    token = generate_print_token(report_id=1, session_id=101, user_id=42)
    record = validate_print_token(token, expected_session_id=999)
    assert record is None


def test_validate_wrong_purpose_returns_none():
    token = generate_print_token(report_id=1, session_id=101, user_id=42)
    record = validate_print_token(token, expected_session_id=101, expected_purpose="other")
    assert record is None


def test_token_allows_multiple_reads():
    token = generate_print_token(report_id=1, session_id=101, user_id=42)
    r1 = validate_print_token(token, expected_session_id=101)
    r2 = validate_print_token(token, expected_session_id=101)
    assert r1 is not None
    assert r2 is not None
    assert r2["read_count"] >= r1["read_count"]


def test_token_unknown_returns_none():
    record = validate_print_token("nonexistent-token", expected_session_id=101)
    assert record is None


def test_consume_token_removes_it():
    token = generate_print_token(report_id=1, session_id=101, user_id=42)
    consume_print_token(token)
    record = validate_print_token(token, expected_session_id=101)
    assert record is None


# ── 11.5 Storage save_bytes ──


@pytest.mark.anyio
async def test_save_bytes_returns_relative_and_absolute(tmp_path: Path):
    storage = StorageService()
    storage.upload_dir = tmp_path

    result = await storage.save_bytes(
        b"%PDF-1.4 test",
        relative_path="reports/1/report_v1.pdf",
        content_type="application/pdf",
    )

    assert result["relative_path"] == "reports/1/report_v1.pdf"
    assert result["absolute_path"].endswith("reports/1/report_v1.pdf")
    assert result["size_bytes"] == 13
    assert (tmp_path / "reports/1/report_v1.pdf").exists()


def test_resolve_path(tmp_path: Path):
    storage = StorageService()
    storage.upload_dir = tmp_path

    resolved = storage.resolve_path("reports/1/report_v1.pdf")
    assert resolved == tmp_path / "reports/1/report_v1.pdf"


@pytest.mark.anyio
async def test_save_bytes_creates_parent_dirs(tmp_path: Path):
    storage = StorageService()
    storage.upload_dir = tmp_path

    deep_path = "a/b/c/d/report.pdf"
    await storage.save_bytes(b"data", relative_path=deep_path)
    assert (tmp_path / deep_path).exists()


# ── Mock API 测试（无 DB） ──


def test_export_missing_session_returns_404():
    """session 不存在时抛 404。"""
    from fastapi import HTTPException
    import pytest

    with pytest.raises(HTTPException) as exc:
        raise HTTPException(status_code=404, detail="训练记录不存在")

    assert exc.value.status_code == 404


def test_export_report_not_found_returns_404():
    """report 不存在时抛 404。"""
    from fastapi import HTTPException
    import pytest

    with pytest.raises(HTTPException) as exc:
        raise HTTPException(status_code=404, detail="报告不存在")

    assert exc.value.status_code == 404


def test_export_already_exporting_returns_409():
    """pdf_status=exporting → 409。"""
    from fastapi import HTTPException
    import pytest

    with pytest.raises(HTTPException) as exc:
        raise HTTPException(status_code=409, detail="PDF is already exporting")

    assert exc.value.status_code == 409


# ── 7.1 _pdf_state_error helper 单元测试 ──


def test_pdf_state_error_not_exported():
    from fastapi import HTTPException
    import pytest

    from app.api.routes.report_exports import _raise_pdf_state_error

    from app.models import ReportMetadata
    report = ReportMetadata(pdf_status="not_exported", pdf_path=None)

    with pytest.raises(HTTPException) as exc:
        _raise_pdf_state_error(report, session_id=101)

    assert exc.value.status_code == 404
    assert exc.value.detail["code"] == "pdf_not_exported"


def test_pdf_state_error_exporting():
    from fastapi import HTTPException
    import pytest

    from app.api.routes.report_exports import _raise_pdf_state_error

    from app.models import ReportMetadata
    report = ReportMetadata(pdf_status="exporting", pdf_path=None)

    with pytest.raises(HTTPException) as exc:
        _raise_pdf_state_error(report, session_id=101)

    assert exc.value.status_code == 409
    assert exc.value.detail["code"] == "pdf_export_in_progress"


def test_pdf_state_error_export_failed():
    from fastapi import HTTPException
    import pytest

    from app.api.routes.report_exports import _raise_pdf_state_error

    from app.models import ReportMetadata
    report = ReportMetadata(pdf_status="export_failed", pdf_path=None)

    with pytest.raises(HTTPException) as exc:
        _raise_pdf_state_error(report, session_id=101)

    assert exc.value.status_code == 409
    assert exc.value.detail["code"] == "pdf_export_failed"


def test_pdf_state_error_exported_but_null_path():
    from fastapi import HTTPException
    import pytest

    from app.api.routes.report_exports import _raise_pdf_state_error

    from app.models import ReportMetadata
    report = ReportMetadata(pdf_status="exported", pdf_path=None)

    with pytest.raises(HTTPException) as exc:
        _raise_pdf_state_error(report, session_id=101)

    assert exc.value.status_code == 404
    assert exc.value.detail["code"] == "pdf_not_exported"


def test_pdf_state_error_unknown_status():
    from fastapi import HTTPException
    import pytest

    from app.api.routes.report_exports import _raise_pdf_state_error

    from app.models import ReportMetadata
    report = ReportMetadata(pdf_status="unknown_stale", pdf_path=None)

    with pytest.raises(HTTPException) as exc:
        _raise_pdf_state_error(report, session_id=101)

    assert exc.value.status_code == 404
    assert exc.value.detail["code"] == "pdf_not_exported"


# ── 2.5 AsyncMock 回归测试 ──


@pytest.mark.anyio
async def test_export_pdf_awaits_save_bytes():
    from app.services.pdf_export_service import PdfExportService

    mock_db = MagicMock()
    mock_report = MagicMock()
    mock_report.id = 1
    mock_report.pdf_version = 0
    mock_report.pdf_path = None
    mock_report.pdf_status = "not_exported"
    mock_report.pdf_exported_at = None
    mock_db.get.return_value = mock_report

    mock_storage = MagicMock()
    mock_storage.save_bytes = AsyncMock(return_value={
        "relative_path": "reports/1/report_v1.pdf",
        "absolute_path": "/tmp/reports/1/report_v1.pdf",
        "size_bytes": 100,
    })

    service = PdfExportService(db=mock_db, storage=mock_storage)

    with patch(
        "app.services.pdf_export_service.render_pdf_from_url",
        new=AsyncMock(return_value=b"%PDF-1.4 test"),
    ), patch(
        "app.services.pdf_export_service.generate_print_token",
        return_value="test-token",
    ):
        result = await service.export_report_pdf(
            report_id=1,
            session_id=101,
            user_id=42,
        )

    mock_storage.save_bytes.assert_awaited_once_with(
        b"%PDF-1.4 test",
        relative_path="reports/1/report_v1.pdf",
        content_type="application/pdf",
    )


# ── 7.4 resolve_quality_profile_id 单元测试 ──


def test_resolve_profile_cvat():
    from app.services.annotation_quality.profile_resolver import resolve_quality_profile_id
    from app.models.annotation import AnnotationSource

    assert resolve_quality_profile_id("cvat") == "side_technical_v1_cvat"
    assert resolve_quality_profile_id(AnnotationSource.CVAT) == "side_technical_v1_cvat"


def test_resolve_profile_kinovea():
    from app.services.annotation_quality.profile_resolver import resolve_quality_profile_id
    from app.models.annotation import AnnotationSource

    assert resolve_quality_profile_id("kinovea") == "side_technical_v1"
    assert resolve_quality_profile_id(AnnotationSource.KINOVEA) == "side_technical_v1"


def test_resolve_profile_unknown():
    from app.services.annotation_quality.profile_resolver import resolve_quality_profile_id

    assert resolve_quality_profile_id("dartfish") == "side_technical_v1"
    assert resolve_quality_profile_id("manual_json") == "side_technical_v1"


# ── PDF Route 集成测试（Mock DB） ──


def _make_mock_report(**kwargs) -> MagicMock:
    from unittest.mock import MagicMock
    from datetime import datetime, timezone

    report = MagicMock()
    report.id = kwargs.get("id", 1)
    report.session_id = kwargs.get("session_id", 101)
    report.pdf_status = kwargs.get("pdf_status", "not_exported")
    report.pdf_path = kwargs.get("pdf_path", None)
    report.pdf_exported_at = kwargs.get("pdf_exported_at", None)
    report.pdf_error = kwargs.get("pdf_error", None)
    report.pdf_version = kwargs.get("pdf_version", 0)
    report.report_data = kwargs.get("report_data", {"sections": []})
    return report


class TestPdfExportRoutes:
    ROUTE = "app.api.routes.report_exports"

    @pytest.fixture(autouse=True)
    def setup(self):
        from unittest.mock import MagicMock
        from app.core.deps import get_current_user
        from app.db.session import get_db
        from app.main import app

        self.mock_user = MagicMock()
        self.mock_user.id = 1
        self.mock_user.username = "test_coach"
        self.mock_user.is_active = True

        async def fake_get_current_user():
            return self.mock_user

        self.mock_db = MagicMock()

        def fake_get_db():
            yield self.mock_db

        app.dependency_overrides[get_current_user] = fake_get_current_user
        app.dependency_overrides[get_db] = fake_get_db
        yield
        app.dependency_overrides.clear()

    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        from app.main import app
        return TestClient(app)

    # ── Export endpoint ──

    def test_export_session_not_found(self, client):
        with patch(f"{self.ROUTE}.require_owned_session") as mock_owner:
            mock_owner.side_effect = HTTPException(
                status_code=404,
                detail={"code": "session_not_found", "message": "训练记录不存在"},
            )
            resp = client.post("/api/v1/sessions/999/report/export/pdf", json={})

        assert resp.status_code == 404
        assert resp.json()["detail"]["code"] == "session_not_found"

    def test_export_report_not_found(self, client):
        self.mock_db.scalar.return_value = None
        with patch(f"{self.ROUTE}.require_owned_session"):
            resp = client.post("/api/v1/sessions/101/report/export/pdf", json={})

        assert resp.status_code == 404
        assert resp.json()["detail"]["code"] == "report_not_found"

    def test_export_already_exporting(self, client):
        self.mock_db.scalar.return_value = _make_mock_report(pdf_status="exporting")
        with patch(f"{self.ROUTE}.require_owned_session"):
            resp = client.post("/api/v1/sessions/101/report/export/pdf", json={})

        assert resp.status_code == 409
        assert resp.json()["detail"]["code"] == "pdf_export_in_progress"

    def test_export_cached_returns_existing(self, client):
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        report = _make_mock_report(
            pdf_status="exported",
            pdf_path="reports/1/report_v1.pdf",
            pdf_exported_at=now,
        )
        self.mock_db.scalar.return_value = report
        with patch(f"{self.ROUTE}.require_owned_session"):
            resp = client.post("/api/v1/sessions/101/report/export/pdf", json={})

        assert resp.status_code == 200
        body = resp.json()
        assert body["pdf_status"] == "exported"
        assert "/api/v1/sessions/101/report/pdf" in body["pdf_url"]

    def test_export_force_retriggers(self, client):
        report = _make_mock_report(
            pdf_status="exported",
            pdf_path="reports/1/report_v1.pdf",
        )
        self.mock_db.scalar.return_value = report
        self.mock_db.execute.return_value.rowcount = 1

        with (
            patch(f"{self.ROUTE}.require_owned_session"),
            patch(f"{self.ROUTE}.PdfExportService") as mock_svc,
        ):
            mock_instance = MagicMock()
            mock_instance.export_report_pdf = AsyncMock(return_value={
                "report_id": 1,
                "pdf_status": "exported",
                "pdf_url": "/api/v1/sessions/101/report/pdf",
                "pdf_exported_at": "2026-07-14T00:00:00+00:00",
            })
            mock_svc.return_value = mock_instance
            resp = client.post("/api/v1/sessions/101/report/export/pdf", json={"force": True})

        assert resp.status_code == 200
        assert resp.json()["pdf_status"] == "exported"

    # ── Download endpoint ──

    def test_download_report_not_found(self, client):
        with patch(f"{self.ROUTE}._resolve_current_owned_report") as mock_resolve:
            mock_resolve.side_effect = HTTPException(
                status_code=404,
                detail={"code": "report_not_found", "message": "当前训练记录尚无报告"},
            )
            resp = client.get("/api/v1/sessions/101/report/pdf")

        assert resp.status_code == 404
        assert resp.json()["detail"]["code"] == "report_not_found"

    def test_download_pdf_not_exported(self, client):
        report = _make_mock_report(pdf_status="not_exported", pdf_path=None)
        with patch(f"{self.ROUTE}._resolve_current_owned_report", return_value=report):
            resp = client.get("/api/v1/sessions/101/report/pdf")

        assert resp.status_code == 404
        assert resp.json()["detail"]["code"] == "pdf_not_exported"

    def test_download_pdf_exporting(self, client):
        report = _make_mock_report(pdf_status="exporting", pdf_path=None)
        with patch(f"{self.ROUTE}._resolve_current_owned_report", return_value=report):
            resp = client.get("/api/v1/sessions/101/report/pdf")

        assert resp.status_code == 409
        assert resp.json()["detail"]["code"] == "pdf_export_in_progress"

    def test_download_pdf_export_failed(self, client):
        report = _make_mock_report(pdf_status="export_failed", pdf_path=None)
        with patch(f"{self.ROUTE}._resolve_current_owned_report", return_value=report):
            resp = client.get("/api/v1/sessions/101/report/pdf")

        assert resp.status_code == 409
        assert resp.json()["detail"]["code"] == "pdf_export_failed"

    def test_download_pdf_exported_but_path_null(self, client):
        """exported + pdf_path=null → 500 pdf_artifact_missing"""
        report = _make_mock_report(pdf_status="exported", pdf_path=None)
        with patch(f"{self.ROUTE}._resolve_current_owned_report", return_value=report):
            resp = client.get("/api/v1/sessions/101/report/pdf")

        assert resp.status_code == 500
        assert resp.json()["detail"]["code"] == "pdf_artifact_missing"

    def test_download_pdf_artifact_missing(self, client):
        """exported + file does not exist → 500 pdf_artifact_missing"""
        report = _make_mock_report(
            pdf_status="exported",
            pdf_path="reports/1/missing.pdf",
        )
        from pathlib import Path
        with (
            patch(f"{self.ROUTE}._resolve_current_owned_report", return_value=report),
            patch(f"{self.ROUTE}.StorageService") as mock_storage_cls,
        ):
            mock_storage = MagicMock()
            mock_storage.resolve_path.return_value = Path("/tmp/nonexistent.pdf")
            mock_storage_cls.return_value = mock_storage
            resp = client.get("/api/v1/sessions/101/report/pdf")

        assert resp.status_code == 500
        assert resp.json()["detail"]["code"] == "pdf_artifact_missing"

    def test_download_pdf_success(self, client, tmp_path):
        pdf_file = tmp_path / "report.pdf"
        pdf_file.write_text("%PDF-1.4 test")
        report = _make_mock_report(
            pdf_status="exported",
            pdf_path="reports/1/report_v1.pdf",
        )
        with (
            patch(f"{self.ROUTE}._resolve_current_owned_report", return_value=report),
            patch(f"{self.ROUTE}.StorageService") as mock_storage_cls,
        ):
            mock_storage = MagicMock()
            mock_storage.resolve_path.return_value = pdf_file
            mock_storage_cls.return_value = mock_storage
            resp = client.get("/api/v1/sessions/101/report/pdf")

        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"

    # ── Status endpoint ──

    def test_status_report_not_found(self, client):
        with patch(f"{self.ROUTE}._resolve_current_owned_report") as mock_resolve:
            mock_resolve.side_effect = HTTPException(
                status_code=404,
                detail={"code": "report_not_found"},
            )
            resp = client.get("/api/v1/sessions/101/report/export/pdf/status")

        assert resp.status_code == 404

    def test_status_exported(self, client):
        report = _make_mock_report(
            pdf_status="exported",
            pdf_path="reports/1/report.pdf",
        )
        with patch(f"{self.ROUTE}._resolve_current_owned_report", return_value=report):
            resp = client.get("/api/v1/sessions/101/report/export/pdf/status")

        assert resp.status_code == 200
        assert resp.json()["pdf_status"] == "exported"

    def test_status_exporting(self, client):
        report = _make_mock_report(pdf_status="exporting")
        with patch(f"{self.ROUTE}._resolve_current_owned_report", return_value=report):
            resp = client.get("/api/v1/sessions/101/report/export/pdf/status")

        assert resp.status_code == 200
        assert resp.json()["pdf_status"] == "exporting"

    # ── Internal print-data endpoint ──

    def test_print_data_invalid_token(self, client):
        with patch(f"{self.ROUTE}.validate_print_token", return_value=None):
            resp = client.get(
                "/api/v1/internal/sessions/101/report/print-data?token=bad"
            )

        assert resp.status_code == 401
        assert resp.json()["detail"]["code"] == "invalid_print_token"

    def test_print_data_report_mismatch(self, client):
        claims = {"report_id": 2, "session_id": 101, "purpose": "pdf_export"}
        with (
            patch(f"{self.ROUTE}.validate_print_token", return_value=claims),
            patch(f"{self.ROUTE}.ReportMetadata") as mock_model,
        ):
            mock_report = MagicMock()
            mock_report.session_id = 999  # doesn't match URL
            mock_report.report_data = {"sections": []}
            mock_model.get.return_value = mock_report
            resp = client.get(
                "/api/v1/internal/sessions/101/report/print-data?token=valid"
            )

        assert resp.status_code == 404
        assert resp.json()["detail"]["code"] == "report_not_found"

    # ── Old path ──

    def test_old_pdf_path_returns_404(self, client):
        resp = client.post(
            "/api/v1/reports/sessions/1/report/export/pdf",
            json={},
        )
        assert resp.status_code == 404
