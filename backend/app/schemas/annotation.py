from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models import AnnotationFileStatus, AnnotationSource, ViewType


class AnnotationFileCreate(BaseModel):
    """上传标注文件的请求参数（文件本身通过 multipart/form-data 传递）。"""

    source: AnnotationSource = AnnotationSource.KINOVEA
    annotation_fps: float | None = Field(default=None, ge=0)
    metadata: dict = Field(default_factory=dict)


class AnnotationFileRead(BaseModel):
    """标注文件列表项和详情响应。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    session_video_id: int
    source: AnnotationSource
    original_filename: str
    stored_filename: str
    storage_path: str
    file_type: str | None
    file_size_bytes: int | None
    checksum_sha256: str | None
    annotation_fps: float | None
    frame_count: int | None
    duration_sec: float | None
    version: int
    status: AnnotationFileStatus
    parse_error: str | None
    metadata: dict
    uploaded_by: int | None
    uploaded_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AnnotationFileListItem(BaseModel):
    """标注文件列表项（精简字段），包含从 session_video 继承的 view_type。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    session_video_id: int
    source: AnnotationSource
    view_type: ViewType | None = None
    file_type: str | None
    version: int
    status: AnnotationFileStatus
    original_filename: str
    annotation_fps: float | None
    uploaded_at: datetime | None


class AnnotationFileDetail(BaseModel):
    """标注文件详情（含 session 和 video 上下文）。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    session_video_id: int
    session_id: int | None = None
    video_file_id: int | None = None
    view_type: ViewType | None = None
    source: AnnotationSource
    original_filename: str
    stored_filename: str
    storage_path: str
    file_type: str | None
    file_size_bytes: int | None
    checksum_sha256: str | None
    annotation_fps: float | None
    frame_count: int | None
    duration_sec: float | None
    version: int
    status: AnnotationFileStatus
    parse_error: str | None
    metadata: dict
    uploaded_by: int | None
    uploaded_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AnnotationFileArchiveResponse(BaseModel):
    """归档操作响应。"""

    id: int
    status: AnnotationFileStatus
