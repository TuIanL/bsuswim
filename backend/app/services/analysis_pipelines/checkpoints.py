"""Checkpoint-aware task state writer for annotation_kinematics pipeline.

与 legacy model_service 的 `_set_task_state` / `_mark_failed` 完全隔离，不直接
修改它们。本 writer 负责写入 execution_state / attempt_count / failed_stage /
error_code，并在失败时先 rollback、再用独立 SessionLocal 记录，避免
PendingRollbackError 卡在 processing。
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models import (
    AnalysisTask,
    AnalysisTaskStatus,
    ReportMetadata,
    TrainingSession,
    TrainingSessionStatus,
)

STAGE_PROGRESS = {
    "queued": 5,
    "validating_input": 10,
    "calculating_metrics": 25,
    "generating_artifacts": 45,
    "running_findings": 65,
    "saving_result": 78,
    "assembling_report": 88,
    "completed": 100,
}

EXECUTION_SCHEMA_VERSION = "analysis-execution.v1"


def _new_execution_state(pipeline_type: str, pipeline_version: str, input_info: dict) -> dict:
    return {
        "schema_version": EXECUTION_SCHEMA_VERSION,
        "attempt": 1,
        "pipeline": {"type": pipeline_type, "version": pipeline_version},
        "input": input_info,
        "steps": {},
        "warnings": [],
    }


def _apply_failure(task: AnalysisTask, stage: str, code: str, message: str) -> None:
    task.status = AnalysisTaskStatus.FAILED
    task.stage = "failed"
    task.progress = max(task.progress or 0, 1)
    task.failed_stage = stage
    task.error_code = code
    task.error_message = message
    state = dict(task.execution_state or {})
    state["previous_failure"] = {"stage": stage, "code": code, "message": message}
    task.execution_state = state


def _record_failure_independent(task_id: int, stage: str, code: str, message: str) -> None:
    with SessionLocal() as db:
        task = db.get(AnalysisTask, task_id)
        if not task:
            return
        _apply_failure(task, stage, code, message)
        db.commit()


class PipelineTaskStateWriter:
    def __init__(self, db: Session, task: AnalysisTask):
        self.db = db
        self.task = task

    def init_execution_state(self, pipeline_type: str, pipeline_version: str, input_info: dict) -> None:
        if not self.task.execution_state:
            self.task.execution_state = _new_execution_state(pipeline_type, pipeline_version, input_info)
            self._commit()

    def claim(self) -> None:
        self.task.attempt_count += 1
        self._set_stage("validating_input", AnalysisTaskStatus.PROCESSING)
        state = dict(self.task.execution_state or {})
        state["attempt"] = self.task.attempt_count
        self.task.execution_state = state
        self._commit()

    def start_step(self, stage: str) -> None:
        state = dict(self.task.execution_state or {})
        state.setdefault("steps", {})
        state["steps"][stage] = {"status": "running"}
        self.task.execution_state = state
        self._set_stage(stage, AnalysisTaskStatus.PROCESSING)
        self._commit()

    def complete_step(self, stage: str, **extra) -> None:
        state = dict(self.task.execution_state or {})
        state.setdefault("steps", {})
        step = dict(state["steps"].get(stage, {}))
        step["status"] = "completed"
        step.update(extra)
        state["steps"][stage] = step
        self.task.execution_state = state
        self._commit()

    def add_warning(self, warning: str) -> None:
        state = dict(self.task.execution_state or {})
        warnings = list(state.get("warnings", []))
        warnings.append(warning)
        state["warnings"] = warnings
        self.task.execution_state = state
        self._commit()

    def complete_pipeline(self, report_id: int | None = None) -> None:
        self.task.status = AnalysisTaskStatus.COMPLETED
        self.task.stage = "completed"
        self.task.progress = 100
        self.task.error_code = None
        self.task.error_message = None
        self.task.completed_at = datetime.utcnow()
        self._commit()
        refresh_session_analysis_status(self.db, self.task.session_id)

    def fail(self, stage: str, code: str, message: str) -> None:
        try:
            _apply_failure(self.task, stage, code, message)
            self.db.add(self.task)
            self.db.flush()
            self.db.commit()
        except Exception:
            self.db.rollback()
            _record_failure_independent(self.task.id, stage, code, message)

    def _ensure_state(self) -> dict:
        return dict(self.task.execution_state or {})

    def _set_stage(self, stage: str, status: AnalysisTaskStatus) -> None:
        self.task.stage = stage
        self.task.status = status
        progress = STAGE_PROGRESS.get(stage)
        if progress is not None:
            self.task.progress = max(self.task.progress or 0, progress)

    def _commit(self) -> None:
        self.db.add(self.task)
        self.db.flush()
        self.db.commit()


def refresh_session_analysis_status(db: Session, session_id: int) -> None:
    """根据 session 下所有分析任务推导 TrainingSession.status。

    annotation pipeline 经此写状态，不直接无条件写 session。
    """
    session = db.get(TrainingSession, session_id)
    if not session:
        return
    tasks = db.scalars(select(AnalysisTask).where(AnalysisTask.session_id == session_id)).all()

    if any(t.status in (AnalysisTaskStatus.QUEUED, AnalysisTaskStatus.PROCESSING, AnalysisTaskStatus.RESULT_SAVING) for t in tasks):
        new_status = TrainingSessionStatus.ANALYZING
    else:
        existing_report = db.scalar(select(ReportMetadata.id).where(ReportMetadata.session_id == session_id))
        if any(t.status == AnalysisTaskStatus.COMPLETED for t in tasks) or existing_report is not None:
            new_status = TrainingSessionStatus.COMPLETED
        elif tasks and all(t.status == AnalysisTaskStatus.FAILED for t in tasks):
            new_status = TrainingSessionStatus.FAILED
        else:
            new_status = session.status

    if new_status != session.status:
        session.status = new_status
        db.add(session)
        db.flush()
