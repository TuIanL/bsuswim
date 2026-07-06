from app.schemas.analysis import (
    AnalysisResultRead,
    AnalysisStatusRead,
    AnalysisSubmit,
    AnalysisTaskRead,
    ModelAnalysisRequest,
    ModelAnalysisResult,
    WorkspaceData,
)
from app.schemas.annotation import (
    AnnotationFileArchiveResponse,
    AnnotationFileCreate,
    AnnotationFileDetail,
    AnnotationFileListItem,
    AnnotationFileRead,
)
from app.schemas.athlete import AthleteCreate, AthleteRead
from app.schemas.auth import Token, UserRegister
from app.schemas.normalized_annotation import (
    AnnotationEvent,
    AnnotationQuality,
    CoordinateSystem,
    KeypointFrame,
    ManualTag,
    NormalizedAnnotationCreate,
    NormalizedAnnotationListItem,
    NormalizedAnnotationRead,
    ParseResponse,
    ScaleInfo,
    Trajectory,
    VideoContext,
)
from app.schemas.report import ReportData, ReportGenerate
from app.schemas.training_session import TrainingSessionCreate, TrainingSessionRead
from app.schemas.user import UserRead
from app.schemas.video import SessionVideoCreate, SessionVideoRead, VideoFileRead, VideoUploadResponse

__all__ = [
    "AnalysisResultRead",
    "AnalysisStatusRead",
    "AnalysisSubmit",
    "AnalysisTaskRead",
    "AnnotationFileArchiveResponse",
    "AnnotationFileCreate",
    "AnnotationFileDetail",
    "AnnotationFileListItem",
    "AnnotationFileRead",
    "AnnotationEvent",
    "AnnotationQuality",
    "AthleteCreate",
    "AthleteRead",
    "CoordinateSystem",
    "KeypointFrame",
    "ManualTag",
    "ModelAnalysisRequest",
    "ModelAnalysisResult",
    "NormalizedAnnotationCreate",
    "NormalizedAnnotationListItem",
    "NormalizedAnnotationRead",
    "ParseResponse",
    "ReportData",
    "ReportGenerate",
    "SessionVideoCreate",
    "SessionVideoRead",
    "ScaleInfo",
    "Token",
    "TrainingSessionCreate",
    "TrainingSessionRead",
    "UserRead",
    "UserRegister",
    "VideoFileRead",
    "VideoUploadResponse",
    "WorkspaceData",
]
