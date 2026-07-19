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

# 失败恢复策略注册表（design Decision 22）
# resubmit → 新建任务，后端锁定当前 annotation revision
# retry    → 重跑原任务（沿用锁定 revision）
# details  → 非用户可恢复，仅展示详情
ERROR_RECOVERY_POLICY: dict[str, str] = {
    # 输入/版本类
    "INVALID_INPUT": "resubmit",
    "ANNOTATION_NOT_FOUND": "resubmit",
    "ANNOTATION_REVISION_DRIFT": "resubmit",
    "SESSION_MISMATCH": "resubmit",
    "UNSUPPORTED_VIEW": "resubmit",
    "NO_KEYPOINT_FRAMES": "resubmit",
    # 执行阶段类
    "METRIC_PERSIST_FAILED": "retry",
    "METRIC_REVISION_MISMATCH": "retry",
    "ARTIFACT_GENERATION_FAILED": "retry",
    "REVIEW_FINDINGS_GENERATION_FAILED": "retry",
    "REPORT_ASSEMBLY_FAILED": "retry",
    "PIPELINE_INTERNAL_ERROR": "retry",
    # 非用户可恢复
    "UNSUPPORTED_PIPELINE_VERSION": "details",
    "TASK_OWNER_UNAVAILABLE": "details",
    "QUALITY_BLOCKED": "details",
    # 报告元数据缺失（completed 但无报告实体，design Decision 20/21）：用当前标注重新生成
    "REPORT_METADATA_MISSING": "resubmit",
}

RECOVERY_RESUBMIT = "resubmit"
RECOVERY_RETRY = "retry"
RECOVERY_DETAILS = "details"


def recovery_policy_for(error_code: str | None) -> str:
    if not error_code:
        return RECOVERY_DETAILS
    return ERROR_RECOVERY_POLICY.get(error_code, RECOVERY_DETAILS)
