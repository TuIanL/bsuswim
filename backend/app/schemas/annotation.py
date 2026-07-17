from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models import AnnotationFileStatus, AnnotationSource, ViewType
from app.schemas.normalized_annotation import (
    AnalysisReadiness,
    ParseSummary,
)


QualityStatus = Literal["valid", "warning", "invalid"]


class AnnotationFileCreate(BaseModel):
    source: AnnotationSource = AnnotationSource.KINOVEA
    annotation_fps: float | None = Field(default=None, ge=0)
    metadata: dict = Field(default_factory=dict)


class AnnotationFileRead(BaseModel):
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

    normalized_annotation_id: int | None = None
    normalized_revision: int | None = None
    quality_status: QualityStatus | None = None
    analysis_readiness: AnalysisReadiness | None = None
    parse_warnings: list[str] = Field(default_factory=list)
    parse_error: str | None = None


class AnnotationIngestResponse(BaseModel):
    annotation_file_id: int
    session_video_id: int
    session_id: int
    video_file_id: int

    source: AnnotationSource
    file_status: AnnotationFileStatus
    file_version: int
    original_filename: str

    normalized_annotation_id: int
    normalized_revision: int
    schema_version: str

    parse_summary: ParseSummary
    quality: dict
    analysis_readiness: AnalysisReadiness
    warnings: list[str] = Field(default_factory=list)


class AnnotationFileDetail(BaseModel):
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
    id: int
    status: AnnotationFileStatus
