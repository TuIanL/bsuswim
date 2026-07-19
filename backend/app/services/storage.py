import hashlib
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import get_settings


class UnsafeStoragePath(Exception):
    """Raised when a relative storage path attempts to escape the upload root."""


def _validate_relative_path(upload_dir: Path, relative_path: str) -> Path:
    if not relative_path:
        raise UnsafeStoragePath("empty relative path")
    if "\x00" in relative_path:
        raise UnsafeStoragePath("NUL character in path")
    if Path(relative_path).is_absolute():
        raise UnsafeStoragePath("absolute path not allowed")
    root = upload_dir.resolve()
    destination = (root / relative_path).resolve()
    try:
        destination.relative_to(root)
    except ValueError:
        raise UnsafeStoragePath("path escapes upload root")
    return destination


class StorageService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.upload_dir = self.settings.upload_dir
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    async def save_upload(self, file: UploadFile) -> dict[str, str | int | None]:
        suffix = Path(file.filename or "video").suffix.lower()
        stored_filename = f"{uuid4().hex}{suffix}"
        destination = self.upload_dir / stored_filename
        digest = hashlib.sha256()
        size = 0

        with destination.open("wb") as output:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                digest.update(chunk)
                output.write(chunk)

        return {
            "original_filename": file.filename or stored_filename,
            "stored_filename": stored_filename,
            "storage_path": str(destination),
            "mime_type": file.content_type,
            "size_bytes": size,
            "checksum_sha256": digest.hexdigest(),
        }


    async def save_bytes(
        self,
        data: bytes,
        relative_path: str,
        content_type: str = "application/pdf",
    ) -> dict:
        destination = _validate_relative_path(self.upload_dir, relative_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        checksum = hashlib.sha256(data).hexdigest()
        return {
            "relative_path": relative_path,
            "absolute_path": str(destination),
            "size_bytes": len(data),
            "checksum_sha256": checksum,
            "mime_type": content_type,
        }

    def resolve_path(self, relative_path: str) -> Path:
        return self.upload_dir / relative_path


def public_asset_url(relative_path: str) -> str:
    """Build a public URL for a stored relative path under /uploads."""
    return f"/uploads/{relative_path}"


def playback_url(stored_filename: str) -> str:
    return f"/uploads/{stored_filename}"
