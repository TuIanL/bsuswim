from pathlib import Path

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.models.annotation import AnnotationFile, AnnotationFileStatus, AnnotationSource
from app.repositories.annotation_repository import get_max_version, get_with_ownership_check
from app.services.storage import StorageService

ALLOWED_FILE_EXTENSIONS: dict[str, str] = {
    ".csv": "csv",
    ".json": "json",
    ".xml": "xml",
    ".txt": "txt",
    ".kva": "kva",
}

MAX_ANNOTATION_FILE_SIZE_BYTES: int = 50 * 1024 * 1024  # 50 MB


def detect_file_type(original_filename: str) -> str:
    """根据文件扩展名推断 file_type。"""
    suffix = Path(original_filename).suffix.lower()
    return ALLOWED_FILE_EXTENSIONS.get(suffix, "unknown")


def validate_annotation_file(file: UploadFile) -> None:
    """校验标注文件：非空、类型在允许列表中。"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="上传的标注文件名为空")

    file_type = detect_file_type(file.filename)
    if file_type == "unknown":
        raise HTTPException(
            status_code=400,
            detail="当前仅支持 csv、json、xml、txt、kva 格式的标注文件",
        )


async def create_annotation(
    db: Session,
    *,
    file: UploadFile,
    session_video_id: int,
    source: AnnotationSource,
    annotation_fps: float | None,
    metadata: dict | None,
    uploaded_by: int,
) -> AnnotationFile:
    """保存标注文件并创建数据库记录。"""
    validate_annotation_file(file)

    # 复用现有存储服务
    saved = await StorageService().save_upload(file)

    file_type = detect_file_type(saved["original_filename"])

    # 计算版本号
    max_ver = get_max_version(db, session_video_id, source)
    version = max_ver + 1

    annotation = AnnotationFile(
        session_video_id=session_video_id,
        source=source,
        original_filename=saved["original_filename"],
        stored_filename=saved["stored_filename"],
        storage_path=saved["storage_path"],
        file_type=file_type,
        file_size_bytes=saved["size_bytes"],
        checksum_sha256=saved["checksum_sha256"],
        annotation_fps=annotation_fps,
        version=version,
        status=AnnotationFileStatus.UPLOADED,
        uploaded_by=uploaded_by,
        metadata=metadata or {},
    )
    db.add(annotation)
    db.commit()
    db.refresh(annotation)
    return annotation


def archive_annotation(
    db: Session,
    annotation_file_id: int,
    current_user_id: int,
) -> AnnotationFile:
    """归档标注文件（不物理删除）。"""
    annotation = get_with_ownership_check(db, annotation_file_id, current_user_id)
    annotation.status = AnnotationFileStatus.ARCHIVED
    db.add(annotation)
    db.commit()
    db.refresh(annotation)
    return annotation
