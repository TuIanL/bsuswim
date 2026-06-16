from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.api.routes.videos import _read_video
from app.db.session import get_db
from app.models import AnalysisResult, AnalysisTask, VideoFile
from app.schemas import AnalysisResultRead, AnalysisTaskCreate, AnalysisTaskRead, WorkspaceData
from app.services.analysis_service import create_analysis_task, run_analysis_task, task_actions

router = APIRouter()


@router.post("", response_model=AnalysisTaskRead, status_code=status.HTTP_201_CREATED)
async def create_task(
    payload: AnalysisTaskCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> AnalysisTaskRead:
    video = db.get(VideoFile, payload.video_id)
    if not video:
        raise HTTPException(status_code=404, detail="视频不存在")

    task = create_analysis_task(db, payload)
    background_tasks.add_task(run_analysis_task, task.id)
    task.video = video
    return _read_task(task)


@router.get("", response_model=list[AnalysisTaskRead])
def list_tasks(db: Session = Depends(get_db)) -> list[AnalysisTaskRead]:
    tasks = db.scalars(
        select(AnalysisTask).options(joinedload(AnalysisTask.video)).order_by(AnalysisTask.updated_at.desc())
    ).all()
    return [_read_task(task) for task in tasks]


@router.get("/{task_id}", response_model=AnalysisTaskRead)
def get_task(task_id: int, db: Session = Depends(get_db)) -> AnalysisTaskRead:
    task = db.get(AnalysisTask, task_id, options=[joinedload(AnalysisTask.video)])
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return _read_task(task)


@router.get("/{task_id}/workspace", response_model=WorkspaceData)
def get_workspace(task_id: int, db: Session = Depends(get_db)) -> WorkspaceData:
    task = db.get(AnalysisTask, task_id, options=[joinedload(AnalysisTask.video), joinedload(AnalysisTask.result)])
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    result = None
    if task.result:
        result = AnalysisResultRead.model_validate(task.result)
    return WorkspaceData(task=_read_task(task), result=result)


@router.get("/{task_id}/result", response_model=AnalysisResultRead)
def get_result(task_id: int, db: Session = Depends(get_db)) -> AnalysisResultRead:
    result = db.scalar(select(AnalysisResult).where(AnalysisResult.task_id == task_id))
    if not result:
        raise HTTPException(status_code=404, detail="分析结果不存在")
    return AnalysisResultRead.model_validate(result)


def _read_task(task: AnalysisTask) -> AnalysisTaskRead:
    video = _read_video(task.video) if task.video else None
    return AnalysisTaskRead.model_validate(
        {
            **task.__dict__,
            "video": video,
            "actions": task_actions(task),
        }
    )
