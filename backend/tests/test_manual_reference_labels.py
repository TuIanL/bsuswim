"""人工时序参考标注：契约级测试（需测试数据库，跟随 conftest 的 db_session）。

覆盖 design/tasks 关键不变量：
* content_hash 稳定性与规范化（排除非语义字段、固定小数位）
* fork 继承 cycle_id、相同内容可保存（无 UNIQUE(set_id, content_hash)）
* 离开 draft（含 in_review）后内容不可改（409 语义）
* side 收敛：both/unknown 仅允许 draft
* resolver 仅显式引用、无 latest 入口、失效不回退
* 双向 adapter 派生与不回写
"""

from datetime import datetime

import pytest
from sqlalchemy import select

from app.models.analysis import AnalysisTask, AnalysisTaskStatus
from app.models.manual_reference_label import (
    ManualAnnotationRevision,
    ManualPhaseSegment,
    ManualRevisionStatus,
    SegmentDerivation,
)
from app.services.reference_labels.adapter import (
    events_to_segments,
    segments_to_events,
    time_sec_to_frame,
)
from app.services.reference_labels.errors import EditVersionConflictError, RevisionImmutableError
from app.services.reference_labels.hashing import compute_segments_hash
from app.services.reference_labels.profile import get_phase_profile
from app.services.reference_labels.resolver import (
    STATUS_LEGACY,
    STATUS_REFERENCE_INVALID,
    resolve_for_analysis_task,
)
from app.services.reference_labels.service import (
    create_segment,
    create_set,
    fork_revision,
    review_pass,
    submit_review,
    update_segment,
)
from app.services.reference_labels.validation import run_validation

PROFILE = "freestyle_arm_phase_v1"


def _seg_dict(cycle_id, side, phase_code, start, end, note="n"):
    return {
        "cycle_id": cycle_id, "side": side, "phase_code": phase_code,
        "start_time_sec": start, "end_time_sec": end, "confidence": None, "note": note,
    }


def _full_cycle(db_session, revision, cycle_id="cycle-X", side="left"):
    """写入一个完整四阶段 cycle。"""
    for ph, s, e in [("entry", 0.0, 0.5), ("catch", 0.5, 1.0), ("push", 1.0, 1.5), ("recovery", 1.5, 2.0)]:
        create_segment(db_session, revision_id=revision.id, edit_version=revision.edit_version, created_by=1,
                       cycle_id=cycle_id, side=side, phase_code=ph, start_time_sec=s, end_time_sec=e)


# ── content_hash 规范化 ──


def test_content_hash_deterministic_and_excludes_non_semantic():
    segs = [
        _seg_dict("c1", "left", "entry", 0.0, 0.5, note="a"),
        _seg_dict("c1", "left", "catch", 0.5, 1.0, note="b"),
    ]
    h1 = compute_segments_hash(segs)
    # 顺序不影响
    assert compute_segments_hash(list(reversed(segs))) == h1
    # 非语义字段（id / revision_id / cycle_index / 时间戳）不参与
    with_nonsemantic = [
        {**s, "id": 999, "revision_id": 42, "cycle_index": 3,
         "created_at": "2026-01-01", "updated_at": "2026-01-02"}
        for s in segs
    ]
    assert compute_segments_hash(with_nonsemantic) == h1
    # 浮点表示差异不影响（0.1+0.2 类问题）
    assert compute_segments_hash([_seg_dict("c1", "left", "entry", 0.3, 0.8)]) == \
        compute_segments_hash([_seg_dict("c1", "left", "entry", 0.3, 0.8)])
    # note 是语义字段，改变会改变 hash
    changed_note = [_seg_dict("c1", "left", "entry", 0.0, 0.5, note="different"),
                    _seg_dict("c1", "left", "catch", 0.5, 1.0, note="x")]
    assert compute_segments_hash(changed_note) != h1


def test_content_hash_excludes_soft_deleted():
    segs = [_seg_dict("c1", "left", "entry", 0.0, 0.5)]
    h_with = compute_segments_hash(segs)
    segs_del = [_seg_dict("c1", "left", "entry", 0.0, 0.5),
                {**_seg_dict("c1", "left", "catch", 0.5, 1.0), "deleted_at": datetime.now()}]
    assert compute_segments_hash(segs_del) == h_with


# ── fork / 不可变 / 乐观锁 ──


def test_fork_inherits_cycle_id_and_same_content_saves(db_session, test_session_video):
    annotation_set, rev = create_set(db_session, session_video_id=test_session_video.id,
                                     phase_profile_id=PROFILE, created_by=1)
    _full_cycle(db_session, rev)
    content_before = rev.content_hash

    # 提交复核 + 复核通过（锁定，但只需 L1+L2，不触发 L3 的两周期要求）
    submit_review(db_session, revision_id=rev.id, actor=1)
    reviewed = review_pass(db_session, revision_id=rev.id, actor=1)

    new_rev = fork_revision(db_session, revision_id=reviewed.id, created_by=2)
    assert new_rev.status == ManualRevisionStatus.DRAFT
    forked_segs = db_session.scalars(
        select(ManualPhaseSegment).where(ManualPhaseSegment.revision_id == new_rev.id)
    ).all()
    # fork 继承同一 cycle_id（不是重新生成）
    assert {s.cycle_id for s in forked_segs} == {"cycle-X"}
    # 相同内容 → 相同 content_hash（验证无 UNIQUE(set_id, content_hash) 约束）
    assert new_rev.content_hash == content_before


def test_immutable_after_leaving_draft(db_session, test_session_video):
    _, rev = create_set(db_session, session_video_id=test_session_video.id,
                        phase_profile_id=PROFILE, created_by=1)
    _full_cycle(db_session, rev)
    submit_review(db_session, revision_id=rev.id, actor=1)  # 离开 draft → in_review 即锁
    with pytest.raises(RevisionImmutableError):
        create_segment(db_session, revision_id=rev.id, edit_version=rev.edit_version, created_by=1,
                       cycle_id="cycle-Y", side="left", phase_code="entry",
                       start_time_sec=2.0, end_time_sec=2.5)


def test_optimistic_lock_conflict(db_session, test_session_video):
    _, rev = create_set(db_session, session_video_id=test_session_video.id,
                        phase_profile_id=PROFILE, created_by=1)
    seg = create_segment(db_session, revision_id=rev.id, edit_version=rev.edit_version, created_by=1,
                         cycle_id="cycle-X", side="left", phase_code="entry",
                         start_time_sec=0.0, end_time_sec=0.5)
    with pytest.raises(EditVersionConflictError):
        # 携带过期的 edit_version
        update_segment(db_session, segment_id=seg.id, edit_version=rev.edit_version - 1, updated_by=1,
                       start_time_sec=0.1, end_time_sec=0.6)


# ── side 收敛 ──


def test_side_converge_blocks_non_draft(db_session, test_session_video):
    _, rev = create_set(db_session, session_video_id=test_session_video.id,
                        phase_profile_id=PROFILE, created_by=1)
    # both 在 draft 可存
    create_segment(db_session, revision_id=rev.id, edit_version=rev.edit_version, created_by=1,
                   cycle_id="cycle-X", side="both", phase_code="entry",
                   start_time_sec=0.0, end_time_sec=0.5)
    # 提交复核时 L2 side 收敛 MUST 拦截
    with pytest.raises(RevisionImmutableError):
        submit_review(db_session, revision_id=rev.id, actor=1)


def test_side_convergence_rule_in_l2(db_session, test_session_video):
    """both/unknown 仅 draft 允许；发布态被 L2 拦截。"""
    segs = [_seg_dict("c1", "unknown", "entry", 0.0, 0.5)]
    profile = get_phase_profile(PROFILE)
    # draft 不要求收敛
    assert run_validation(segs, profile, ManualRevisionStatus.DRAFT).ok
    # 发布态要求收敛
    result = run_validation(segs, profile, ManualRevisionStatus.IN_REVIEW)
    assert not result.ok
    assert any(e.code == "SIDE_NOT_CONVERGED" for e in result.errors)


# ── resolver ──


def test_resolver_only_explicit_no_latest(db_session, test_session_video, test_session):
    _, rev = create_set(db_session, session_video_id=test_session_video.id,
                        phase_profile_id=PROFILE, created_by=1)
    task = AnalysisTask(session_id=test_session.id, status=AnalysisTaskStatus.QUEUED,
                        reference_annotation_revision_id=rev.id)
    db_session.add(task)
    db_session.commit()
    # draft revision 引用 → reference_input_invalid，MUST NOT 回退
    assert resolve_for_analysis_task(db_session, task).status == STATUS_REFERENCE_INVALID

    # NULL 引用 → legacy（保持 imported events 行为），不存在 latest 推断路径
    task.reference_annotation_revision_id = None
    db_session.commit()
    assert resolve_for_analysis_task(db_session, task).status == STATUS_LEGACY


def test_resolver_ready_for_reviewed_revision(db_session, test_session_video, test_session):
    _, rev = create_set(db_session, session_video_id=test_session_video.id,
                        phase_profile_id=PROFILE, created_by=1)
    _full_cycle(db_session, rev)
    submit_review(db_session, revision_id=rev.id, actor=1)
    review_pass(db_session, revision_id=rev.id, actor=1)

    task = AnalysisTask(session_id=test_session.id, status=AnalysisTaskStatus.QUEUED,
                        reference_annotation_revision_id=rev.id)
    db_session.add(task)
    db_session.commit()

    res = resolve_for_analysis_task(db_session, task)
    assert res.status == "ready"
    assert res.revision is not None and res.revision.id == rev.id
    assert len(res.segments) == 4


# ── adapter ──


def test_adapter_roundtrip_and_no_writeback():
    profile = get_phase_profile(PROFILE)
    segs = [
        ManualPhaseSegment(revision_id=1, cycle_id="c", side="left", phase_code="entry",
                           start_time_sec=0.0, end_time_sec=0.5, derivation=SegmentDerivation.MANUAL),
        ManualPhaseSegment(revision_id=1, cycle_id="c", side="left", phase_code="catch",
                           start_time_sec=0.5, end_time_sec=1.0, derivation=SegmentDerivation.MANUAL),
        ManualPhaseSegment(revision_id=1, cycle_id="c", side="left", phase_code="push",
                           start_time_sec=1.0, end_time_sec=1.5, derivation=SegmentDerivation.MANUAL),
        ManualPhaseSegment(revision_id=1, cycle_id="c", side="left", phase_code="recovery",
                           start_time_sec=1.5, end_time_sec=2.0, derivation=SegmentDerivation.MANUAL),
    ]
    events = segments_to_events(segs, profile, revision_id=1)
    names = {e.name for e in events}
    assert {"hand_entry", "catch_start", "pull_end", "hand_exit"} <= names
    # 派生结果不回写：原始 segment 的 derivation 未被改写
    assert all(s.derivation is SegmentDerivation.MANUAL for s in segs)

    # events → segments 缺 hand_exit → partial，禁止猜测
    partial = events_to_segments(
        [{"name": "hand_entry", "time_sec": 0.0, "side": "left"},
         {"name": "catch_start", "time_sec": 0.5, "side": "left"},
         {"name": "pull_end", "time_sec": 1.0, "side": "left"}],
        profile,
    )
    assert not partial.complete
    assert "hand_exit" in partial.missing_boundaries
    assert any("recovery_unavailable" in n for n in partial.notes)


def test_events_to_segments_complete_when_all_boundaries():
    profile = get_phase_profile(PROFILE)
    result = events_to_segments(
        [{"name": "hand_entry", "time_sec": 0.0, "side": "left"},
         {"name": "catch_start", "time_sec": 0.5, "side": "left"},
         {"name": "pull_end", "time_sec": 1.0, "side": "left"},
         {"name": "hand_exit", "time_sec": 1.5, "side": "left"},
         {"name": "hand_entry", "time_sec": 2.0, "side": "left"}],
        profile,
    )
    assert result.complete and not result.missing_boundaries
    codes = {s["phase_code"] for s in result.segments}
    assert codes == {"entry", "catch", "push", "recovery"}


def test_time_sec_to_frame_requires_fps():
    assert time_sec_to_frame(1.0, 30) == 30
    assert time_sec_to_frame(1.0, None) is None  # 缺 frame_basis 不猜测
