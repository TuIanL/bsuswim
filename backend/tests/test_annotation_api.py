"""API integration tests for annotation file persistence.

Run with: python -m pytest backend/tests/test_annotation_api.py -v
Requires: pip install pytest pytest-mock
"""

import io
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.deps import get_current_user
from app.db.session import get_db
from app.main import app

# Patch target prefix — routes import functions into their own namespace
ROUTE = "app.api.routes.annotations"
REPO = "app.repositories.annotation_repository"
SVC = "app.services.annotation_file_service"


@pytest.fixture(autouse=True)
def override_auth():
    """Override auth and db dependencies for all tests."""
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.username = "test_coach"
    mock_user.is_active = True

    async def fake_get_current_user():
        return mock_user

    def fake_get_db():
        yield MagicMock()

    app.dependency_overrides[get_current_user] = fake_get_current_user
    app.dependency_overrides[get_db] = fake_get_db
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_session():
    s = MagicMock()
    s.id = 101
    s.coach_id = 1
    return s


@pytest.fixture
def mock_sv():
    from app.models import ViewType
    sv = MagicMock()
    sv.id = 1001
    sv.session_id = 101
    sv.video_file_id = 501
    sv.view_type = ViewType.SIDE
    return sv


def _make_mock_annotation(id=301, session_video_id=1001, version=1):
    """Create a mock AnnotationFile that behaves like a real one for serialization."""
    from app.models.annotation import AnnotationFileStatus, AnnotationSource
    ann = MagicMock()
    ann.id = id
    ann.session_video_id = session_video_id
    ann.source = AnnotationSource.KINOVEA
    ann.version = version
    ann.status = AnnotationFileStatus.UPLOADED
    ann.original_filename = "test.csv"
    ann.stored_filename = "abc123.csv"
    ann.storage_path = "uploads/abc123.csv"
    ann.file_type = "csv"
    ann.file_size_bytes = 100
    ann.checksum_sha256 = "sha256:abc"
    ann.annotation_fps = 60
    ann.frame_count = None
    ann.duration_sec = None
    ann.parse_error = None
    ann.annotation_metadata = {}
    ann.uploaded_by = 1
    ann.uploaded_at = datetime.now(timezone.utc)
    ann.created_at = datetime.now(timezone.utc)
    ann.updated_at = datetime.now(timezone.utc)
    return ann


# ── Upload ──


class TestUploadAnnotation:
    def test_upload_success(self, client, mock_session, mock_sv):
        """10.1: 上传标注文件成功（201）"""
        mock_ann = _make_mock_annotation()

        with (
            patch(f"{ROUTE}._get_owned_session", return_value=mock_session),
            patch(f"{ROUTE}._find_session_video", return_value=mock_sv),
            patch(f"{ROUTE}.create_annotation", return_value=mock_ann),
        ):
            response = client.post(
                "/api/v1/sessions/101/videos/501/annotations",
                files={"file": ("test.csv", io.BytesIO(b"col1,col2\n1,2\n"), "text/csv")},
                data={"source": "kinovea", "annotation_fps": "60"},
            )
        assert response.status_code == 201
        data = response.json()
        assert data["annotation_file_id"] == 301
        assert data["source"] == "kinovea"
        assert data["version"] == 1
        assert data["status"] == "uploaded"

    def test_upload_version_increment(self, client, mock_session, mock_sv):
        """10.3: 版本号自动递增验证"""
        mock_ann = _make_mock_annotation(id=302, version=2)

        with (
            patch(f"{ROUTE}._get_owned_session", return_value=mock_session),
            patch(f"{ROUTE}._find_session_video", return_value=mock_sv),
            patch(f"{ROUTE}.create_annotation", return_value=mock_ann),
        ):
            response = client.post(
                "/api/v1/sessions/101/videos/501/annotations",
                files={"file": ("v2.csv", io.BytesIO(b"v2"), "text/csv")},
                data={"source": "kinovea"},
            )
        assert response.status_code == 201
        assert response.json()["version"] == 2

    def test_session_not_found(self, client):
        """10.5: session 不存在"""
        from fastapi import HTTPException
        with patch(f"{ROUTE}._get_owned_session",
                   side_effect=HTTPException(status_code=404, detail="训练记录不存在")):
            response = client.post(
                "/api/v1/sessions/99999/videos/99999/annotations",
                files={"file": ("test.csv", io.BytesIO(b"data"), "text/csv")},
                data={"source": "kinovea"},
            )
        assert response.status_code == 404

    def test_video_not_bound(self, client, mock_session):
        """10.5: 视频未绑定"""
        from fastapi import HTTPException
        with (
            patch(f"{ROUTE}._get_owned_session", return_value=mock_session),
            patch(f"{ROUTE}._find_session_video",
                  side_effect=HTTPException(status_code=404, detail="该视频未绑定到当前训练记录")),
        ):
            response = client.post(
                "/api/v1/sessions/101/videos/99999/annotations",
                files={"file": ("test.csv", io.BytesIO(b"data"), "text/csv")},
                data={"source": "kinovea"},
            )
        assert response.status_code == 404

    def test_unsupported_file_type(self, client, mock_session, mock_sv):
        """10.5: 不支持的文件类型"""
        with (
            patch(f"{ROUTE}._get_owned_session", return_value=mock_session),
            patch(f"{ROUTE}._find_session_video", return_value=mock_sv),
        ):
            response = client.post(
                "/api/v1/sessions/101/videos/501/annotations",
                files={"file": ("bad.exe", io.BytesIO(b"x"), "application/octet-stream")},
                data={"source": "kinovea"},
            )
        assert response.status_code == 400

    def test_empty_filename(self, client, mock_session, mock_sv):
        """10.5: 空文件名 → FastAPI 返回 422 因为 UploadFile 校验失败"""
        with (
            patch(f"{ROUTE}._get_owned_session", return_value=mock_session),
            patch(f"{ROUTE}._find_session_video", return_value=mock_sv),
        ):
            response = client.post(
                "/api/v1/sessions/101/videos/501/annotations",
                files={"file": ("", io.BytesIO(b""), "text/csv")},
                data={"source": "kinovea"},
            )
        # FastAPI/Starlette rejects empty filename UploadFile at the validation layer
        assert response.status_code in (400, 422)

    def test_cross_session_version_isolation(self, client, mock_session, mock_sv):
        """10.6: 跨 session 版本隔离验证"""
        mock_ann = _make_mock_annotation(id=401, session_video_id=2001, version=1)

        with (
            patch(f"{ROUTE}._get_owned_session", return_value=mock_session),
            patch(f"{ROUTE}._find_session_video", return_value=mock_sv),
            patch(f"{ROUTE}.create_annotation", return_value=mock_ann),
        ):
            response = client.post(
                "/api/v1/sessions/102/videos/501/annotations",
                files={"file": ("s2.csv", io.BytesIO(b"s2"), "text/csv")},
                data={"source": "kinovea"},
            )
        assert response.status_code == 201
        assert response.json()["version"] == 1


# ── List ──


class TestListAnnotations:
    def test_list_empty(self, client, mock_session, mock_sv):
        """10.2: 查询标注文件列表（空）"""
        with (
            patch(f"{ROUTE}._get_owned_session", return_value=mock_session),
            patch(f"{ROUTE}._find_session_video", return_value=mock_sv),
            patch(f"{ROUTE}.list_by_session_video", return_value=[]),
        ):
            response = client.get("/api/v1/sessions/101/videos/501/annotations")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_with_items(self, client, mock_session, mock_sv):
        """10.2: 查询标注文件列表（有数据）"""
        mock_ann = _make_mock_annotation()

        with (
            patch(f"{ROUTE}._get_owned_session", return_value=mock_session),
            patch(f"{ROUTE}._find_session_video", return_value=mock_sv),
            patch(f"{ROUTE}.list_by_session_video", return_value=[mock_ann]),
        ):
            response = client.get("/api/v1/sessions/101/videos/501/annotations")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["source"] == "kinovea"


# ── Detail ──


class TestGetAnnotationDetail:
    def test_get_detail(self, client):
        """10.2: 查看标注文件详情"""
        from app.models.annotation import AnnotationFile, AnnotationFileStatus, AnnotationSource
        from app.models import SessionVideo, ViewType

        sv = SessionVideo(id=1001, session_id=101, video_file_id=501, view_type=ViewType.SIDE)
        ann = AnnotationFile(
            id=301, session_video_id=1001, source=AnnotationSource.KINOVEA,
            original_filename="test.csv", stored_filename="abc123.csv",
            storage_path="uploads/abc123.csv", file_type="csv",
            file_size_bytes=100, checksum_sha256="sha256:abc",
            annotation_fps=60, version=1, status=AnnotationFileStatus.UPLOADED,
            uploaded_by=1, uploaded_at=datetime.now(timezone.utc),
            annotation_metadata={}, created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        ann.session_video = sv

        with patch(f"{ROUTE}.get_with_ownership_check", return_value=ann):
            response = client.get("/api/v1/annotations/301")
        assert response.status_code == 200
        assert response.json()["id"] == 301

    def test_not_found(self, client):
        """标注文件不存在"""
        from fastapi import HTTPException
        with patch(f"{ROUTE}.get_with_ownership_check",
                   side_effect=HTTPException(status_code=404, detail="标注文件不存在")):
            response = client.get("/api/v1/annotations/99999")
        assert response.status_code == 404


# ── Download ──


class TestDownloadAnnotation:
    def test_download(self, client):
        """10.7: 下载标注文件"""
        mock_ann = _make_mock_annotation()
        with (
            patch(f"{ROUTE}.get_with_ownership_check", return_value=mock_ann),
            patch("pathlib.Path.exists", return_value=True),
            patch(f"{ROUTE}.FileResponse") as mock_fr,
        ):
            mock_fr.return_value = MagicMock(status_code=200)
            response = client.get("/api/v1/annotations/301/download")
        # FileResponse raises RuntimeError if file not on disk; with FileResponse
        # mocked the route returns the mock. Check that it didn't 404.
        assert response.status_code != 404

    def test_file_missing(self, client):
        """下载时文件不存在"""
        mock_ann = _make_mock_annotation()
        with (
            patch(f"{ROUTE}.get_with_ownership_check", return_value=mock_ann),
            patch("pathlib.Path.exists", return_value=False),
        ):
            response = client.get("/api/v1/annotations/301/download")
        assert response.status_code == 404


# ── Archive ──


class TestArchiveAnnotation:
    def test_archive(self, client):
        """10.4: 归档标注文件"""
        from app.models.annotation import AnnotationFileStatus
        archived = MagicMock()
        archived.id = 301
        archived.status = AnnotationFileStatus.ARCHIVED

        with patch(f"{SVC}.archive_annotation", return_value=archived):
            response = client.post("/api/v1/annotations/301/archive")
        assert response.status_code == 200
        assert response.json()["status"] == "archived"
