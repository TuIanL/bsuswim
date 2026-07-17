from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.api.routes.sessions import _read_session_video
from app.api.routes.videos import _read_video
from app.core.deps import get_current_user
from app.db.session import get_db
from app.models import AnalysisResult, AnalysisTask, SessionVideo, TrainingSession, User
from app.schemas import (
    AnalysisResultRead,
    AnalysisStatusRead,
    AnalysisSubmit,
    AnalysisTaskRead,
    ModelAnalysisResult,
    WorkspaceData,
)
from app.services.analysis_service import (
    AnnotationInputUnavailableError,
    AnnotationQualityBlockedError,
    AnnotationSelectionRequiredError,
    create_analysis_task,
    run_analysis_task,
    save_analysis_result,
    task_actions,
)

router = APIRouter()


@router.post("/submit", response_model=AnalysisTaskRead, status_code=status.HTTP_201_CREATED)
async def submit_analysis(
    payload: AnalysisSubmit,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AnalysisTaskRead:
    session = db.get(
        TrainingSession,
        payload.session_id,
        options=[joinedload(TrainingSession.videos).joinedload(SessionVideo.video_file)],
    )
    if not session or session.coach_id != current_user.id:
        raise HTTPException(status_code=404, detail="训练记录不存在")
    if not session.videos:
        raise HTTPException(status_code=400, detail="训练记录尚未绑定视频")

    try:
        task = create_analysis_task(db, payload)
    except AnnotationQualityBlockedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": {
                    "code": "ANNOTATION_QUALITY_BLOCKED",
                    "message": str(exc),
                    "details": exc.quality,
                }
            },
        )
    except AnnotationSelectionRequiredError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "error": {
                    "code": "ANNOTATION_SELECTION_REQUIRED",
                    "message": str(exc),
                    "candidate_normalized_annotation_ids": exc.candidate_ids,
                }
            },
        )
    except AnnotationInputUnavailableError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "error": {
                    "code": "ANNOTATION_INPUT_UNAVAILABLE",
                    "message": str(exc),
                    "reason": exc.reason,
                }
            },
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    background_tasks.add_task(run_analysis_task, task.id)
    return _read_task(task)


@router.get("", response_model=list[AnalysisTaskRead])
def list_analysis_tasks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AnalysisTaskRead]:
    tasks = db.scalars(
        select(AnalysisTask)
        .join(AnalysisTask.session)
        .where(TrainingSession.coach_id == current_user.id)
        .order_by(AnalysisTask.updated_at.desc())
    ).all()
    return [_read_task(task) for task in tasks]


@router.get("/{task_id}", response_model=AnalysisTaskRead)
def get_analysis_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AnalysisTaskRead:
    task = _get_owned_task(db, task_id, current_user)
    return _read_task(task)


@router.get("/{task_id}/status", response_model=AnalysisStatusRead)
def get_analysis_status(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AnalysisStatusRead:
    task = _get_owned_task(db, task_id, current_user)
    return AnalysisStatusRead(
        task_id=task.id,
        session_id=task.session_id,
        status=task.status,
        progress=task.progress,
        stage=task.stage,
        error_message=task.error_message,
        created_at=task.created_at,
        updated_at=task.updated_at,
        completed_at=task.completed_at,
    )


@router.get("/{task_id}/result", response_model=AnalysisResultRead)
def get_result(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AnalysisResultRead:
    _get_owned_task(db, task_id, current_user)
    result = db.scalar(select(AnalysisResult).where(AnalysisResult.task_id == task_id))
    if not result:
        raise HTTPException(status_code=404, detail="分析结果不存在")
    return AnalysisResultRead.model_validate(result)


@router.get("/{task_id}/workspace", response_model=WorkspaceData)
def get_workspace(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkspaceData:
    task = _get_owned_task(
        db,
        task_id,
        current_user,
        options=[
            joinedload(AnalysisTask.result),
            joinedload(AnalysisTask.session)
            .joinedload(TrainingSession.videos)
            .joinedload(SessionVideo.video_file),
        ],
    )
    session_videos = sorted(task.session.videos if task.session else [], key=lambda item: item.created_at)
    return WorkspaceData(
        task=_read_task(task),
        result=AnalysisResultRead.model_validate(task.result) if task.result else None,
        videos=[_read_video(link.video_file) for link in session_videos if link.video_file],
        session_videos=[_read_session_video(link) for link in session_videos if link.video_file],
    )


@router.post("/{task_id}/result", response_model=AnalysisResultRead)
def save_result(
    task_id: int,
    payload: ModelAnalysisResult,
    db: Session = Depends(get_db),
) -> AnalysisResultRead:
    task = db.get(
        AnalysisTask,
        task_id,
        options=[joinedload(AnalysisTask.session).joinedload(TrainingSession.athlete)],
    )
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    result = save_analysis_result(db, task, payload)
    if not result:
        raise HTTPException(status_code=400, detail=task.error_message or "分析结果保存失败")
    return AnalysisResultRead.model_validate(result)


def _get_owned_task(
    db: Session,
    task_id: int,
    current_user: User,
    options: list | None = None,
) -> AnalysisTask:
    load_options = options or [joinedload(AnalysisTask.session)]
    task = db.get(AnalysisTask, task_id, options=load_options)
    if not task or not task.session or task.session.coach_id != current_user.id:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task


def _read_task(task: AnalysisTask) -> AnalysisTaskRead:
    return AnalysisTaskRead.model_validate({**task.__dict__, "actions": task_actions(task)})


# 挂载诊断子路由（前缀继承 /analysis）：/api/v1/analysis/analysis-results/{id}/diagnostics[/run]
from app.api.routes.diagnostics import router as _diagnostics_router  # noqa: E402

router.include_router(_diagnostics_router)
