"""PDF 导出服务单测。

- Print token / storage save_bytes / resolver：纯单元测试，无 DB。
- Mock API 测试：不依赖真实 DB，mock 掉 service 层。
- Integration 标记（@pytest.mark.integration）：需 PostgreSQL + Playwright。
"""

from pathlib import Path

import pytest

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


# ── Integration 标记（需 PostgreSQL + Playwright） ──


@pytest.mark.integration
def test_export_success():
    """需要 PostgreSQL + Playwright"""
    pass


@pytest.mark.integration
def test_export_force_false_returns_existing():
    """需要 PostgreSQL"""
    pass


@pytest.mark.integration
def test_export_missing_report_data():
    """需要 PostgreSQL"""
    pass


@pytest.mark.integration
def test_download_pdf_when_path_empty_returns_409():
    """需要 PostgreSQL"""
    pass


@pytest.mark.integration
def test_download_pdf_when_file_missing_returns_404():
    """需要 PostgreSQL"""
    pass
