"""Pipeline execution errors for annotation-driven analysis."""
from __future__ import annotations


class PipelineExecutionError(Exception):
    """结构化 pipeline 失败。

    code 对应 design 中定义的可枚举错误码（如 ANNOTATION_REVISION_DRIFT）。
    stage 为失败时的具体阶段字符串。
    """

    def __init__(self, code: str, message: str, stage: str | None = None):
        self.code = code
        self.stage = stage
        self.message = message
        super().__init__(f"[{code}] {message}")


class PipelineNotImplementedError(PipelineExecutionError):
    def __init__(self, pipeline_type: str):
        super().__init__(
            "PIPELINE_NOT_IMPLEMENTED",
            f"pipeline_type={pipeline_type} 尚未实现",
        )


# 常用错误码常量
ERROR_ANNOTATION_REVISION_DRIFT = "ANNOTATION_REVISION_DRIFT"
ERROR_TASK_OWNER_UNAVAILABLE = "TASK_OWNER_UNAVAILABLE"
ERROR_UNSUPPORTED_PIPELINE_VERSION = "UNSUPPORTED_PIPELINE_VERSION"
ERROR_ARTIFACT_GENERATION_FAILED = "ARTIFACT_GENERATION_FAILED"
ERROR_REVIEW_FINDINGS_GENERATION_FAILED = "REVIEW_FINDINGS_GENERATION_FAILED"
ERROR_QUALITY_BLOCKED = "QUALITY_BLOCKED"
