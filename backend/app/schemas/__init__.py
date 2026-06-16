from app.schemas.analysis import (
    AnalysisResultRead,
    AnalysisStatusRead,
    AnalysisSubmit,
    AnalysisTaskRead,
    ModelAnalysisRequest,
    ModelAnalysisResult,
    WorkspaceData,
)
from app.schemas.athlete import AthleteCreate, AthleteRead
from app.schemas.auth import Token, UserRegister
from app.schemas.report import ReportData, ReportGenerate
from app.schemas.training_session import TrainingSessionCreate, TrainingSessionRead
from app.schemas.user import UserRead
from app.schemas.video import SessionVideoCreate, SessionVideoRead, VideoFileRead, VideoUploadResponse

__all__ = [
    "AnalysisResultRead",
    "AnalysisStatusRead",
    "AnalysisSubmit",
    "AnalysisTaskRead",
    "AthleteCreate",
    "AthleteRead",
    "ModelAnalysisRequest",
    "ModelAnalysisResult",
    "ReportData",
    "ReportGenerate",
    "SessionVideoCreate",
    "SessionVideoRead",
    "Token",
    "TrainingSessionCreate",
    "TrainingSessionRead",
    "UserRead",
    "UserRegister",
    "VideoFileRead",
    "VideoUploadResponse",
    "WorkspaceData",
]
