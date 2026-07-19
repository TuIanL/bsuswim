"""model_service pipeline — 保留既有模型服务执行行为，不改写其状态 helper。"""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session, joinedload

from app.db.session import SessionLocal
from app.models import AnalysisTask, AnalysisTaskStatus, TrainingSession, TrainingSessionStatus
from app.schemas import ModelAnalysisRequest, ModelAnalysisResult
from app.services.analysis_service import _mark_failed, _set_task_state, save_analysis_result
from app.services.model_client import ModelServiceClient, ModelServiceError
from app.services.analysis_pipelines.protocols import PipelineOutcome


class ModelServicePipeline:
    pipeline_type = "model_service"
    supported_versions = {"model_service_v1"}

    async def run(self, task_id: int, pipeline_version: str) -> PipelineOutcome:
        db = SessionLocal()
        try:
            task = db.get(
                AnalysisTask,
                task_id,
                options=[joinedload(AnalysisTask.session)],
            )
            if not task:
                return PipelineOutcome(task_id, self.pipeline_type, pipeline_version, completed=False)
            # 沿用既有状态 helper，不做 checkpoint-aware 改造
            _set_task_state(db, task, AnalysisTaskStatus.PROCESSING, "model_inference", 35)
            client = ModelServiceClient()
            request_payload = dict(task.request_payload)
            request_payload["task_id"] = task.id
            request_payload["callback_url"] = f"/api/v1/analysis/{task.id}/result"
            result = await client.analyze(ModelAnalysisRequest.model_validate(request_payload))
            save_analysis_result(db, task, result)
            return PipelineOutcome(task_id, self.pipeline_type, pipeline_version, completed=True)
        except ModelServiceError as exc:
            _mark_failed(db, task_id, str(exc))
            return PipelineOutcome(task_id, self.pipeline_type, pipeline_version, completed=False)
        except Exception as exc:
            _mark_failed(db, task_id, f"分析任务执行失败: {exc}")
            return PipelineOutcome(task_id, self.pipeline_type, pipeline_version, completed=False)
        finally:
            db.close()
