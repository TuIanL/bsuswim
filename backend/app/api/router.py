from fastapi import APIRouter

from app.api.routes import (
    analysis,
    annotations,
    athletes,
    auth,
    kinematic_artifacts,
    metrics,
    normalized_annotations,
    report_exports,
    reports,
    sessions,
    users,
    videos,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(athletes.router, prefix="/athletes", tags=["athletes"])
api_router.include_router(sessions.router, prefix="/sessions", tags=["sessions"])
api_router.include_router(videos.router, prefix="/videos", tags=["videos"])
api_router.include_router(analysis.router, prefix="/analysis", tags=["analysis"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(report_exports.public_router)
api_router.include_router(report_exports.internal_router)
api_router.include_router(annotations.router, tags=["annotations"])
api_router.include_router(normalized_annotations.router, tags=["normalized-annotations"])
api_router.include_router(metrics.router, tags=["metrics"])
api_router.include_router(kinematic_artifacts.router, tags=["kinematic-artifacts"])
