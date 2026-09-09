import asyncio
import io

import pytest
from starlette.datastructures import Headers
from starlette.datastructures import UploadFile

from app.services.storage import StorageService, UploadTooLargeError


def _upload(payload: bytes, filename: str = "fixture.mp4") -> UploadFile:
    return UploadFile(
        file=io.BytesIO(payload),
        filename=filename,
        headers=Headers({"content-type": "application/octet-stream"}),
    )


def _storage(tmp_path) -> StorageService:
    storage = StorageService()
    storage.upload_dir = tmp_path
    return storage


def test_upload_at_limit_is_saved(tmp_path):
    storage = _storage(tmp_path)

    saved = asyncio.run(storage.save_upload(_upload(b"12345"), max_bytes=5))

    assert saved["size_bytes"] == 5
    assert (tmp_path / saved["stored_filename"]).read_bytes() == b"12345"


def test_upload_over_limit_deletes_partial_file(tmp_path):
    storage = _storage(tmp_path)

    with pytest.raises(UploadTooLargeError) as exc_info:
        asyncio.run(storage.save_upload(_upload(b"123456"), max_bytes=5))

    assert exc_info.value.max_bytes == 5
    assert list(tmp_path.iterdir()) == []


def test_upload_limit_is_applied_after_multiple_chunks(tmp_path):
    storage = _storage(tmp_path)

    with pytest.raises(UploadTooLargeError):
        asyncio.run(storage.save_upload(_upload(b"a" * (1024 * 1024 + 1)), max_bytes=1024 * 1024))

    assert list(tmp_path.iterdir()) == []
