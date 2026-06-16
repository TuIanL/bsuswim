import hashlib
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import get_settings


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


def playback_url(stored_filename: str) -> str:
    return f"/uploads/{stored_filename}"
