"""人工参考标注 resolver（显式引用解析）。

设计核心（design D6b / tasks 4.1、4.7、4.9）：

* 解析 **完全由显式引用驱动**。``AnalysisTask.reference_annotation_revision_id``
  为 ``None`` → ``legacy``（消费 imported events）；非 ``None`` → 解析该 revision。
* **MUST NOT** 实现"发现数据库存在 reviewed/frozen revision 就自动切换"的推断；
  同一 session video 存在多个已发布 revision 时系统 MUST NOT 自行挑选。
* 不提供任何「按 session 取 latest」入口。
* 显式引用但不可用（not_found / checksum_mismatch / profile_mismatch）→
  ``reference_input_invalid``，**MUST NOT** 回退到 imported events 或别的 revision。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.manual_reference_label import (
    ManualAnnotationRevision,
    ManualPhaseSegment,
    ManualRevisionStatus,
)
from app.models.video import SessionVideo, VideoFile
from app.services.reference_labels.errors import ResolutionError


@dataclass
class ReferenceLabelResolution:
    status: str
    revision: ManualAnnotationRevision | None = None
    segments: list[ManualPhaseSegment] = field(default_factory=list)
    warnings: list[dict] = field(default_factory=list)
    details: dict = field(default_factory=dict)


# task 显式引用失效时的统一状态
STATUS_REFERENCE_INVALID = "reference_input_invalid"
STATUS_LEGACY = "legacy"
STATUS_READY = "ready"


def resolve_reference_labels(
    db: Session,
    *,
    revision_id: int,
    expected_profile_hash: str | None = None,
) -> ReferenceLabelResolution:
    """显式解析某个 revision。不提供 latest 入口。"""
    revision = db.get(ManualAnnotationRevision, revision_id)
    if revision is None:
        return ReferenceLabelResolution(status="not_found", details={"revision_id": revision_id})

    # 视频校验和交叉校验
    session_video = db.get(SessionVideo, revision.set.session_video_id) if revision.set else None
    current_checksum = None
    if session_video is not None:
        video_file = db.get(VideoFile, session_video.video_file_id)
        current_checksum = video_file.checksum_sha256 if video_file else None
    if current_checksum is None:
        return ReferenceLabelResolution(
            status="checksum_unknown",
            revision=revision,
            details={"recorded": revision.video_checksum_sha256},
        )
    if current_checksum != revision.video_checksum_sha256:
        return ReferenceLabelResolution(
            status="checksum_mismatch",
            revision=revision,
            details={"recorded": revision.video_checksum_sha256, "current": current_checksum},
        )

    # profile hash 交叉校验（任务快照携带时比对）
    if expected_profile_hash is not None and expected_profile_hash != revision.phase_profile_hash:
        return ReferenceLabelResolution(
            status="profile_mismatch",
            revision=revision,
            details={"recorded": revision.phase_profile_hash, "expected": expected_profile_hash},
        )

    segments = (
        db.scalars(
            select(ManualPhaseSegment)
            .where(ManualPhaseSegment.revision_id == revision.id, ManualPhaseSegment.deleted_at.is_(None))
        ).all()
    )
    return ReferenceLabelResolution(status=STATUS_READY, revision=revision, segments=list(segments))


def resolve_for_analysis_task(db: Session, task: Any) -> ReferenceLabelResolution:
    """为分析任务解析参考标注输入。

    返回 ``legacy`` 表示未指定 revision（保持 legacy imported-event 行为）；
    显式引用但不可用一律返回 ``reference_input_invalid``，调用方 MUST 阻断分析。
    """
    revision_id = getattr(task, "reference_annotation_revision_id", None)
    if revision_id is None:
        return ReferenceLabelResolution(status=STATUS_LEGACY)

    expected_hash = None
    ai = (task.request_payload or {}).get("analysis_input", {})
    expected_hash = ai.get("phase_profile_hash")

    res = resolve_reference_labels(db, revision_id=revision_id, expected_profile_hash=expected_hash)
    if res.status != STATUS_READY:
        # 显式引用失效：归一为 reference_input_invalid，MUST NOT 回退
        return ReferenceLabelResolution(
            status=STATUS_REFERENCE_INVALID,
            revision=res.revision,
            warnings=[{"code": res.status, "details": res.details}],
            details=res.details,
        )
    # draft revision 不可作为分析引用（仅 in_review/reviewed/frozen 允许）
    try:
        assert_reference_revision_referenceable(res.revision)
    except ResolutionError:
        return ReferenceLabelResolution(
            status=STATUS_REFERENCE_INVALID,
            revision=res.revision,
            warnings=[{"code": "revision_not_referenceable", "details": {"status": res.revision.status.value}}],
            details={"status": res.revision.status.value},
        )
    return res


def assert_reference_revision_referenceable(revision: ManualAnnotationRevision) -> None:
    """分析任务引用 revision 时 MUST 仅允许 in_review / reviewed / frozen。"""
    if revision.status not in (
        ManualRevisionStatus.IN_REVIEW,
        ManualRevisionStatus.REVIEWED,
        ManualRevisionStatus.FROZEN,
    ):
        raise ResolutionError(
            STATUS_REFERENCE_INVALID,
            f"revision {revision.id} 状态为 {revision.status.value}，draft 不可作为分析引用",
        )
