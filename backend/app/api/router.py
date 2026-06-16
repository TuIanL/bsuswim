from fastapi import APIRouter

from app.api.routes import reports, tasks, videos

api_router = APIRouter()
api_router.include_router(videos.router, prefix="/videos", tags=["videos"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
