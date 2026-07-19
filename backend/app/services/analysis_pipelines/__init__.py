"""Analysis pipeline package (Change 7: annotation-driven analysis pipeline)."""
from app.services.analysis_pipelines.protocols import AnalysisPipeline, PipelineOutcome
from app.services.analysis_pipelines.registry import PIPELINE_REGISTRY, resolve

__all__ = ["AnalysisPipeline", "PipelineOutcome", "PIPELINE_REGISTRY", "resolve"]
