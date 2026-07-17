from dataclasses import dataclass

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.models.annotation import AnnotationFile, AnnotationSource
from app.schemas.annotation import AnnotationIngestResponse
from app.schemas.normalized_annotation import (
    AnalysisReadiness,
    ParseAnnotationOptions,
    ParseSummary,
)
from app.services.annotation_file_service import create_annotation
from app.services.annotation_quality.legacy import normalize_quality_payload
from app.services.annotation_quality.readiness import derive_analysis_readiness
from app.services.normalized_annotation_service import (
    ParseAnnotationResult,
    parse_annotation_file,
)


class AnnotationIngestionError(Exception):
    def __init__(self, code: str, message: str, annotation_file_id: int | None = None):
        self.code = code
        self.annotation_file_id = annotation_file_id
        super().__init__(message)


@dataclass
class AnnotationIngestionResult:
    annotation_file: AnnotationFile
    parse_result: ParseAnnotationResult | None

    def to_response(self, session_id: int, video_file_id: int) -> AnnotationIngestResponse:
        ann = self.annotation_file
        parse = self.parse_result

        if parse is not None:
            na = parse.annotation
            quality = normalize_quality_payload(na.quality or {})
            return AnnotationIngestResponse(
                annotation_file_id=ann.id,
                session_video_id=ann.session_video_id,
                session_id=session_id,
                video_file_id=video_file_id,
                source=ann.source,
                file_status=ann.status,
                file_version=ann.version,
                original_filename=ann.original_filename,
                normalized_annotation_id=na.id,
                normalized_revision=na.revision,
                schema_version=na.schema_version,
                parse_summary=parse.summary,
                quality=quality.model_dump(mode="json"),
                analysis_readiness=derive_analysis_readiness(na.quality or {}) or AnalysisReadiness(),
                warnings=parse.warnings,
            )

        return AnnotationIngestResponse(
            annotation_file_id=ann.id,
            session_video_id=ann.session_video_id,
            session_id=session_id,
            video_file_id=video_file_id,
            source=ann.source,
            file_status=ann.status,
            file_version=ann.version,
            original_filename=ann.original_filename,
            normalized_annotation_id=0,
            normalized_revision=0,
            schema_version="",
            parse_summary=ParseSummary(),
            quality={"status": "invalid"},
            analysis_readiness=AnalysisReadiness(can_submit=False),
            warnings=[],
        )


async def ingest_annotation(
    db: Session,
    *,
    session_video_id: int,
    file: UploadFile,
    source: AnnotationSource,
    annotation_fps: float | None,
    metadata: dict,
    parse_options: ParseAnnotationOptions | None,
    current_user_id: int,
) -> AnnotationIngestionResult:
    annotation_file = await create_annotation(
        db,
        file=file,
        session_video_id=session_video_id,
        source=source,
        annotation_fps=annotation_fps,
        metadata=metadata,
        uploaded_by=current_user_id,
    )

    try:
        parse_result = parse_annotation_file(
            db,
            annotation_file.id,
            current_user_id=current_user_id,
            options=parse_options,
        )
    except Exception:
        return AnnotationIngestionResult(
            annotation_file=annotation_file,
            parse_result=None,
        )

    return AnnotationIngestionResult(
        annotation_file=annotation_file,
        parse_result=parse_result,
    )
