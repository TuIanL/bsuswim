from datetime import datetime

from sqlalchemy.orm import Session, joinedload

from app.db.session import SessionLocal
from app.models import AnalysisResult, AnalysisTask, AnalysisTaskStatus, ReportMetadata
from app.schemas import AnalysisTaskCreate, ModelAnalysisRequest
from app.services.model_client import ModelServiceClient, ModelServiceError
from app.services.report_builder import build_report_data
from app.services.storage import playback_url


def task_actions(task: AnalysisTask) -> list[str]:
    if task.status == AnalysisTaskStatus.COMPLETED:
        return ["workspace", "report"]
    if task.status == AnalysisTaskStatus.FAILED:
        return ["retry", "details"]
    return ["details"]


def create_analysis_task(db: Session, payload: AnalysisTaskCreate) -> AnalysisTask:
    task = AnalysisTask(
        video_id=payload.video_id,
        status=AnalysisTaskStatus.QUEUED,
        progress=5,
        stage="queued",
        session_metadata=payload.metadata.model_dump(),
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


async def run_analysis_task(task_id: int) -> None:
    db = SessionLocal()
    try:
        task = db.get(AnalysisTask, task_id, options=[joinedload(AnalysisTask.video)])
        if not task:
            return

        _set_task_state(db, task, AnalysisTaskStatus.PROCESSING, "model_inference", 35)
        client = ModelServiceClient()
        result = await client.analyze(
            ModelAnalysisRequest(
                task_id=task.id,
                video_path=task.video.storage_path,
                video_url=playback_url(task.video.stored_filename),
                metadata=task.session_metadata,
            )
        )

        _set_task_state(db, task, AnalysisTaskStatus.RESULT_SAVING, "result_saving", 80)
        analysis_result = AnalysisResult(
            task_id=task.id,
            schema_version=result.schema_version,
            detections=result.detections,
            keypoint_frames=result.keypoint_frames,
            phases=result.phases,
            metrics=result.metrics,
            diagnostics=result.diagnostics,
            raw_result=result.model_dump(),
        )
        db.add(analysis_result)
        db.flush()
        db.add(ReportMetadata(task_id=task.id, source="model_service", report_data=build_report_data(task, analysis_result)))
        _set_task_state(db, task, AnalysisTaskStatus.COMPLETED, "completed", 100, completed=True)
    except ModelServiceError as exc:
        _mark_failed(db, task_id, str(exc))
    except Exception as exc:
        _mark_failed(db, task_id, f"分析任务执行失败: {exc}")
    finally:
        db.close()


def _set_task_state(
    db: Session,
    task: AnalysisTask,
    status: AnalysisTaskStatus,
    stage: str,
    progress: int,
    completed: bool = False,
) -> None:
    task.status = status
    task.stage = stage
    task.progress = progress
    task.error_message = None
    if completed:
        task.completed_at = datetime.utcnow()
    db.add(task)
    db.commit()
    db.refresh(task)


def _mark_failed(db: Session, task_id: int, message: str) -> None:
    task = db.get(AnalysisTask, task_id)
    if not task:
        return
    task.status = AnalysisTaskStatus.FAILED
    task.stage = "failed"
    task.progress = max(task.progress, 1)
    task.error_message = message
    db.add(task)
    db.commit()
