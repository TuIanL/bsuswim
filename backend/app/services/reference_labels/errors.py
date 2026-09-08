"""人工参考标注服务的领域异常。"""

from __future__ import annotations


class ReferenceLabelError(Exception):
    """基类。"""


class RevisionImmutableError(ReferenceLabelError):
    """revision 已离开 draft，内容不可修改。"""


class EditVersionConflictError(ReferenceLabelError):
    """乐观锁冲突：携带的 edit_version 与当前不一致。"""


class ResolutionError(ReferenceLabelError):
    """resolver 解析失败（非 ready）。"""

    def __init__(self, status: str, message: str, *, details: dict | None = None):
        super().__init__(message)
        self.status = status
        self.details = details or {}
