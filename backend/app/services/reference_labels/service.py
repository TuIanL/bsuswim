"""人工参考标注高层服务（CRUD / fork / 生命周期 / 快照）。

薄封装，供 API 路由调用。所有写操作在 draft revision 上执行，离开 draft 后依赖
``validation.assert_revision_mutable`` 拒绝（in_review 即锁内容）。
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.manual_reference_label import (
    ManualAnnotationRevision,
    ManualAnnotationSet,
    ManualPhaseSegment,
    ManualRevisionStatus,
    PhaseCode,
    SegmentDerivation,
    SegmentSide,
)
from app.models.video import SessionVideo, VideoFile
from app.services.reference_labels.errors import EditVersionConflictError, RevisionImmutableError
from app.services.reference_labels.hashing import compute_segments_hash
from app.services.reference_labels.profile import get_phase_profile
from app.services.reference_labels.validation import assert_revision_mutable, run_validation


def _snapshot_revision_context(db: Session, session_video_id: int, profile_id: str) -> dict:
    """快照视频与 profile 的可复现信息到 revision。"""
    sv = db.get(SessionVideo, session_video_id)
    checksum = None
    fps = None
    if sv is not None:
        vf = db.get(VideoFile, sv.video_file_id)
        checksum = vf.checksum_sha256 if vf else None
        fps = float(sv.fps) if sv.fps is not None else None
    profile = get_phase_profile(profile_id)
    frame_basis = {
        "fps": fps,
        "fps_source": "session_video",
        "mapping_mode": "uniform",
        "mapping_verified": False,
    }
    return {
        "video_checksum_sha256": checksum,
        "video_fps_snapshot": fps,
        "video_duration_snapshot": None,  # 当前无时长来源，保留字段待未来补充
        "frame_basis": frame_basis,
        "phase_profile_id": profile.id,
        "phase_profile_version": profile.version,
        "phase_profile_hash": profile.profile_hash,
    }


def _next_revision_no(db: Session, set_id: int) -> int:
    current = db.scalar(
        select(ManualAnnotationRevision.revision_no)
        .where(ManualAnnotationRevision.set_id == set_id)
        .order_by(ManualAnnotationRevision.revision_no.desc())
        .limit(1)
    )
    return (current or 0) + 1


def _recompute_content_hash(revision: ManualAnnotationRevision, db: Session) -> None:
    segs = (
        db.scalars(
            select(ManualPhaseSegment).where(
                ManualPhaseSegment.revision_id == revision.id, ManualPhaseSegment.deleted_at.is_(None)
            )
        ).all()
    )
    revision.content_hash = compute_segments_hash(list(segs))
    revision.segment_count = len(segs)
    revision.cycle_count = len({s.cycle_id for s in segs})


def create_set(
    db: Session, *, session_video_id: int, phase_profile_id: str, created_by: int | None
) -> tuple[ManualAnnotationSet, ManualAnnotationRevision]:
    """创建 set 并同时创建首个 draft revision（快照当前视频+profile）。"""
    snapshot = _snapshot_revision_context(db, session_video_id, phase_profile_id)
    annotation_set = ManualAnnotationSet(
        session_video_id=session_video_id,
        phase_profile_id=phase_profile_id,
        created_by=created_by,
    )
    db.add(annotation_set)
    db.flush()
    revision = ManualAnnotationRevision(
        set_id=annotation_set.id,
        revision_no=1,
        status=ManualRevisionStatus.DRAFT,
        created_by=created_by,
        # content_hash 为 NOT NULL：flush 前 MUST 有初值（空集的 hash）
        content_hash=compute_segments_hash([]),
        **snapshot,
    )
    db.add(revision)
    db.flush()
    annotation_set.head_revision_id = revision.id
    db.commit()
    db.refresh(annotation_set)
    db.refresh(revision)
    return annotation_set, revision


def list_sets(db: Session, session_video_id: int) -> list[ManualAnnotationSet]:
    return list(
        db.scalars(
            select(ManualAnnotationSet)
            .where(ManualAnnotationSet.session_video_id == session_video_id, ManualAnnotationSet.deleted_at.is_(None))
            .order_by(ManualAnnotationSet.id.desc())
        ).all()
    )


def get_revision(db: Session, revision_id: int) -> ManualAnnotationRevision | None:
    return db.get(ManualAnnotationRevision, revision_id)


def list_segments(db: Session, revision_id: int) -> list[ManualPhaseSegment]:
    return list(
        db.scalars(
            select(ManualPhaseSegment)
            .where(ManualPhaseSegment.revision_id == revision_id, ManualPhaseSegment.deleted_at.is_(None))
            .order_by(ManualPhaseSegment.cycle_id, ManualPhaseSegment.start_time_sec)
        ).all()
    )


def _make_segment(
    *, revision_id: int, cycle_id: str, side: str, phase_code: str,
    start_time_sec: float, end_time_sec: float,
    confidence: float | None = None, note: str | None = None,
    derivation: SegmentDerivation = SegmentDerivation.MANUAL, created_by: int | None = None,
) -> ManualPhaseSegment:
    return ManualPhaseSegment(
        revision_id=revision_id,
        cycle_id=cycle_id,
        side=SegmentSide(side),
        phase_code=PhaseCode(phase_code),
        start_time_sec=start_time_sec,
        end_time_sec=end_time_sec,
        confidence=confidence,
        note=note,
        derivation=derivation,
        created_by=created_by,
    )


def create_segment(
    db: Session, *, revision_id: int, edit_version: int, created_by: int | None, **fields
) -> ManualPhaseSegment:
    revision = db.get(ManualAnnotationRevision, revision_id)
    if revision is None:
        raise RevisionImmutableError("revision 不存在")
    assert_revision_mutable(revision, expected_edit_version=edit_version)
    seg = _make_segment(revision_id=revision_id, created_by=created_by, **fields)
    db.add(seg)
    revision.edit_version += 1
    revision.updated_by = created_by
    db.flush()
    _recompute_content_hash(revision, db)
    db.commit()
    db.refresh(seg)
    return seg


def update_segment(
    db: Session, *, segment_id: int, edit_version: int, updated_by: int | None, **fields
) -> ManualPhaseSegment:
    seg = db.get(ManualPhaseSegment, segment_id)
    if seg is None or seg.deleted_at is not None:
        raise RevisionImmutableError("segment 不存在")
    revision = db.get(ManualAnnotationRevision, seg.revision_id)
    assert_revision_mutable(revision, expected_edit_version=edit_version)
    for key in ("cycle_id", "side", "phase_code", "start_time_sec", "end_time_sec", "confidence", "note"):
        if key in fields and fields[key] is not None:
            value = fields[key]
            if key == "side":
                value = SegmentSide(value)
            elif key == "phase_code":
                value = PhaseCode(value)
            setattr(seg, key, value)
    seg.updated_by = updated_by
    revision.edit_version += 1
    revision.updated_by = updated_by
    db.flush()
    _recompute_content_hash(revision, db)
    db.commit()
    db.refresh(seg)
    return seg


def delete_segment(db: Session, *, segment_id: int, edit_version: int, updated_by: int | None) -> None:
    seg = db.get(ManualPhaseSegment, segment_id)
    if seg is None or seg.deleted_at is not None:
        raise RevisionImmutableError("segment 不存在")
    revision = db.get(ManualAnnotationRevision, seg.revision_id)
    assert_revision_mutable(revision, expected_edit_version=edit_version)
    seg.deleted_at = datetime.now()
    seg.updated_by = updated_by
    revision.edit_version += 1
    revision.updated_by = updated_by
    db.flush()
    _recompute_content_hash(revision, db)
    db.commit()


def fork_revision(db: Session, *, revision_id: int, created_by: int | None) -> ManualAnnotationRevision:
    """从指定 revision fork 出新 draft revision。

    继承相同 ``cycle_id``（同一周期跨 revision 稳定）；保留 ``note``；
    重置 ``review_status`` / ``reviewed_by``；重新快照当前视频与 profile。
    """
    src = db.get(ManualAnnotationRevision, revision_id)
    if src is None:
        raise RevisionImmutableError("源 revision 不存在")
    annotation_set = db.get(ManualAnnotationSet, src.set_id)
    snapshot = _snapshot_revision_context(db, annotation_set.session_video_id, src.phase_profile_id)
    new_revision = ManualAnnotationRevision(
        set_id=src.set_id,
        revision_no=_next_revision_no(db, src.set_id),
        forked_from_revision_id=src.id,
        status=ManualRevisionStatus.DRAFT,
        created_by=created_by,
        review_status=None,
        reviewed_by=None,
        reviewed_at=None,
        # flush 前 MUST 有初值，随后在复制完 segment 后重算
        content_hash=src.content_hash,
        **snapshot,
    )
    db.add(new_revision)
    db.flush()
    # 复制 segment，继承 cycle_id
    src_segs = list_segments(db, src.id)
    for s in src_segs:
        db.add(
            _make_segment(
                revision_id=new_revision.id,
                cycle_id=s.cycle_id,  # 继承，不生成新 UUID
                side=s.side.value,
                phase_code=s.phase_code.value,
                start_time_sec=float(s.start_time_sec),
                end_time_sec=float(s.end_time_sec),
                confidence=float(s.confidence) if s.confidence is not None else None,
                note=s.note,
                derivation=s.derivation,
                created_by=created_by,
            )
        )
    db.flush()
    _recompute_content_hash(new_revision, db)
    annotation_set.head_revision_id = new_revision.id
    db.commit()
    db.refresh(new_revision)
    return new_revision


# ── 生命周期 ──


def _transition(db: Session, revision: ManualAnnotationRevision, target: ManualRevisionStatus, *, actor: int | None) -> None:
    segs = list_segments(db, revision.id)
    profile = get_phase_profile(revision.phase_profile_id)
    duration = revision.video_duration_snapshot
    result = run_validation(segs, profile, target, duration_sec=duration)
    if not result.ok:
        raise RevisionImmutableError(
            f"revision {revision.id} 进入 {target.value} 校验未通过: "
            + "; ".join(f"[{e.level}/{e.code}] {e.message}" for e in result.errors)
        )
    revision.status = target
    revision.updated_by = actor
    if target in (ManualRevisionStatus.REVIEWED, ManualRevisionStatus.FROZEN):
        revision.reviewed_by = actor
        revision.reviewed_at = datetime.now()
        revision.review_status = target.value
    db.commit()


def submit_review(db: Session, *, revision_id: int, actor: int | None) -> ManualAnnotationRevision:
    revision = db.get(ManualAnnotationRevision, revision_id)
    if revision is None:
        raise RevisionImmutableError("revision 不存在")
    if not revision.status.is_mutable:
        raise RevisionImmutableError("revision 已离开 draft，提交复核需先 fork")
    _transition(db, revision, ManualRevisionStatus.IN_REVIEW, actor=actor)
    return revision


def review_pass(db: Session, *, revision_id: int, actor: int | None) -> ManualAnnotationRevision:
    revision = db.get(ManualAnnotationRevision, revision_id)
    if revision is None or revision.status != ManualRevisionStatus.IN_REVIEW:
        raise RevisionImmutableError("仅 in_review revision 可复核通过")
    _transition(db, revision, ManualRevisionStatus.REVIEWED, actor=actor)
    return revision


def reject_revision(db: Session, *, revision_id: int, actor: int | None) -> ManualAnnotationRevision:
    revision = db.get(ManualAnnotationRevision, revision_id)
    if revision is None or revision.status != ManualRevisionStatus.IN_REVIEW:
        raise RevisionImmutableError("仅 in_review revision 可打回")
    _transition(db, revision, ManualRevisionStatus.REJECTED, actor=actor)
    return revision


def freeze_revision(db: Session, *, revision_id: int, actor: int | None) -> ManualAnnotationRevision:
    revision = db.get(ManualAnnotationRevision, revision_id)
    if revision is None or revision.status != ManualRevisionStatus.REVIEWED:
        raise RevisionImmutableError("仅 reviewed revision 可冻结")
    _transition(db, revision, ManualRevisionStatus.FROZEN, actor=actor)
    return revision
