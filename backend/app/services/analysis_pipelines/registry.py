"""Pipeline registry — 统一 resolve，dispatcher 不再按类型分派。"""
from __future__ import annotations

from app.services.analysis_pipelines.annotation_kinematics import AnnotationKinematicsPipeline
from app.services.analysis_pipelines.errors import PipelineNotImplementedError
from app.services.analysis_pipelines.model_service import ModelServicePipeline
from app.services.analysis_pipelines.protocols import AnalysisPipeline

PIPELINE_REGISTRY: dict[str, AnalysisPipeline] = {
    "model_service": ModelServicePipeline(),
    "annotation_kinematics": AnnotationKinematicsPipeline(),
}

# hybrid 仅保留类型边界，不注册实现


def resolve(pipeline_type: str) -> AnalysisPipeline:
    pipeline = PIPELINE_REGISTRY.get(pipeline_type)
    if pipeline is None:
        raise PipelineNotImplementedError(pipeline_type)
    return pipeline
