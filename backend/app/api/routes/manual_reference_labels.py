"""人工参考标注工作台 API 路由。

所有权校验：操作均通过 ``session_video_id`` 或 ``revision_id`` → ``set`` →
``session_video`` 关联，确保不越权。写操作在 draft revision 上执行，离开 draft
后返回 409（in_review 即锁内容）。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models import SessionVideo, User
from app.models.manual_reference_label import ManualAnnotationRevision, ManualAnnotationSet, ManualPhaseSegment
from app.schemas.manual_reference_label import (
    ForkResponse,
    PhaseProfileRead,
    RevisionRead,
    SegmentCreate,
    SegmentRead,
    SegmentUpdate,
    SetCreate,
    SetRead,
)
from app.services.reference_labels.errors import EditVersionConflictError, RevisionImmutableError
from app.services.reference_labels.profile import PhaseProfileError, get_phase_profile
from app.services.reference_labels.service import (
    create_segment,
    create_set,
    delete_segment,
    fork_revision,
    freeze_revision,
    list_segments,
    list_sets,
    reject_revision,
    review_pass,
    submit_review,
    update_segment,
)

router = APIRouter()


def _not_found(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def _conflict(exc: Exception) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={"error": {"code": "REVISION_LOCKED", "message": str(exc)}},
    )


def _load_set_for_video(db: Session, session_video_id: int) -> SessionVideo:
    sv = db.get(SessionVideo, session_video_id)
    if sv is None:
        raise _not_found("session_video 不存在")
    return sv


@router.post(
    "/session-videos/{session_video_id}/manual-annotation-sets",
    response_model=SetRead,
    status_code=status.HTTP_201_CREATED,
)
def create_set_endpoint(session_video_id: int, data: SetCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _load_set_for_video(db, session_video_id)
    try:
        get_phase_profile(data.phase_profile_id)  # 校验 profile 存在且结构合法
    except PhaseProfileError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    annotation_set, _ = create_set(
        db, session_video_id=session_video_id, phase_profile_id=data.phase_profile_id, created_by=current_user.id
    )
    return annotation_set


@router.get("/session-videos/{session_video_id}/manual-annotation-sets", response_model=list[SetRead])
def list_sets_endpoint(session_video_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _load_set_for_video(db, session_video_id)
    return list_sets(db, session_video_id)


@router.get("/manual-annotation-revisions/{revision_id}", response_model=RevisionRead)
def get_revision_endpoint(revision_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    revision = db.get(ManualAnnotationRevision, revision_id)
    if revision is None or revision.deleted_at is not None:
        raise _not_found("revision 不存在")
    return revision


@router.get("/manual-annotation-revisions/{revision_id}/segments", response_model=list[SegmentRead])
def list_segments_endpoint(revision_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if db.get(ManualAnnotationRevision, revision_id) is None:
        raise _not_found("revision 不存在")
    return list_segments(db, revision_id)


@router.post(
    "/manual-annotation-revisions/{revision_id}/segments",
    response_model=SegmentRead,
    status_code=status.HTTP_201_CREATED,
)
def create_segment_endpoint(revision_id: int, data: SegmentCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if db.get(ManualAnnotationRevision, revision_id) is None:
        raise _not_found("revision 不存在")
    try:
        return create_segment(
            db, revision_id=revision_id, edit_version=data.edit_version, created_by=current_user.id,
            cycle_id=data.cycle_id, side=data.side, phase_code=data.phase_code,
            start_time_sec=data.start_time_sec, end_time_sec=data.end_time_sec,
            confidence=data.confidence, note=data.note,
        )
    except (RevisionImmutableError, EditVersionConflictError) as exc:
        raise _conflict(exc)


@router.patch("/manual-phase-segments/{segment_id}", response_model=SegmentRead)
def update_segment_endpoint(segment_id: int, data: SegmentUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if db.get(ManualPhaseSegment, segment_id) is None:
        raise _not_found("segment 不存在")
    try:
        return update_segment(
            db, segment_id=segment_id, edit_version=data.edit_version, updated_by=current_user.id,
            cycle_id=data.cycle_id, side=data.side, phase_code=data.phase_code,
            start_time_sec=data.start_time_sec, end_time_sec=data.end_time_sec,
            confidence=data.confidence, note=data.note,
        )
    except (RevisionImmutableError, EditVersionConflictError) as exc:
        raise _conflict(exc)


@router.delete("/manual-phase-segments/{segment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_segment_endpoint(segment_id: int, edit_version: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if db.get(ManualPhaseSegment, segment_id) is None:
        raise _not_found("segment 不存在")
    try:
        delete_segment(db, segment_id=segment_id, edit_version=edit_version, updated_by=current_user.id)
    except (RevisionImmutableError, EditVersionConflictError) as exc:
        raise _conflict(exc)


@router.post("/manual-annotation-revisions/{revision_id}/fork", response_model=ForkResponse)
def fork_endpoint(revision_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        rev = fork_revision(db, revision_id=revision_id, created_by=current_user.id)
    except RevisionImmutableError as exc:
        raise _not_found(str(exc))
    return ForkResponse(
        id=rev.id, set_id=rev.set_id, revision_no=rev.revision_no,
        forked_from_revision_id=rev.forked_from_revision_id, status=rev.status.value,
    )


@router.post("/manual-annotation-revisions/{revision_id}/submit-review", response_model=RevisionRead)
def submit_review_endpoint(revision_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        return submit_review(db, revision_id=revision_id, actor=current_user.id)
    except RevisionImmutableError as exc:
        raise _conflict(exc)


@router.post("/manual-annotation-revisions/{revision_id}/review-pass", response_model=RevisionRead)
def review_pass_endpoint(revision_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        return review_pass(db, revision_id=revision_id, actor=current_user.id)
    except RevisionImmutableError as exc:
        raise _conflict(exc)


@router.post("/manual-annotation-revisions/{revision_id}/reject", response_model=RevisionRead)
def reject_endpoint(revision_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        return reject_revision(db, revision_id=revision_id, actor=current_user.id)
    except RevisionImmutableError as exc:
        raise _conflict(exc)


@router.post("/manual-annotation-revisions/{revision_id}/freeze", response_model=RevisionRead)
def freeze_endpoint(revision_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        return freeze_revision(db, revision_id=revision_id, actor=current_user.id)
    except RevisionImmutableError as exc:
        raise _conflict(exc)


@router.get("/phase-profiles/{phase_profile_id}", response_model=PhaseProfileRead)
def get_phase_profile_endpoint(phase_profile_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        p = get_phase_profile(phase_profile_id)
    except PhaseProfileError as exc:
        raise _not_found(str(exc))
    return PhaseProfileRead(
        id=p.id, version=p.version, cycle_partition_by=p.cycle_partition_by, cycle_boundary=p.cycle_boundary,
        phases=[{"code": ph.code, "display": ph.display, "start": ph.start, "end": ph.end} for ph in p.phases],
        required_boundaries=list(p.required_boundaries),
        optional_boundaries=list(p.optional_boundaries),
        boundary_definitions={name: {
            "name": bd.name, "display": bd.display,
            "operational_definition": bd.operational_definition,
            "reference_joint": bd.reference_joint,
            "annotation_guidance": bd.annotation_guidance,
        } for name, bd in p.boundary_definitions.items()},
    )
