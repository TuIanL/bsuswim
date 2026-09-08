"""人工时序参考标注（manual temporal reference labels）持久化模型。

本模块承载「人工 reference labels → 不可变版本 → 分析快照 → 未来 ML 数据资产」
主线的底层数据契约。设计要点（来自 Change ``add-manual-temporal-reference-labeling-workspace``）：

* ``ManualAnnotationSet`` 表示一条视频上的一套逻辑标注谱系（lineage），不承担
  可复现快照；真正的可复现快照全部落在 ``ManualAnnotationRevision`` 上。
* ``ManualAnnotationRevision`` 是具备版本身份的标注版本：``draft`` 可编辑，
  一旦离开 ``draft``（含 ``in_review``）内容永久锁定，修改只能通过 ``fork`` 出
  新的 ``draft`` revision 完成，且仍属同一 set。
* ``ManualPhaseSegment`` 只通过 ``revision_id`` FK 归属，不冗余 ``set_id``；
  ``cycle_id`` 是跨 revision 稳定的逻辑周期标识（fork 继承、新增才生成、删除
  不复用），不是全局唯一键。

所有时间以 ``start_time_sec`` / ``end_time_sec`` 为 canonical source of truth；
``start_frame`` / ``end_frame`` 仅作带 ``frame_basis`` 的派生快照，不得成为
第二套独立权威时间。
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import (
    JSON,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

SCHEMA_VERSION = "manual-reference-labels.v1"


class ManualRevisionStatus(str, PyEnum):
    """revision 生命周期状态。"""

    DRAFT = "draft"
    IN_REVIEW = "in_review"
    REVIEWED = "reviewed"
    FROZEN = "frozen"
    REJECTED = "rejected"

    @property
    def is_mutable(self) -> bool:
        """只有 draft 允许修改内容。"""
        return self is ManualRevisionStatus.DRAFT


class SegmentSide(str, PyEnum):
    LEFT = "left"
    RIGHT = "right"
    BOTH = "both"
    UNKNOWN = "unknown"

    @property
    def is_publishable(self) -> bool:
        """reviewed / frozen 数据只允许 left / right。"""
        return self in (SegmentSide.LEFT, SegmentSide.RIGHT)


class PhaseCode(str, PyEnum):
    ENTRY = "entry"
    CATCH = "catch"
    PUSH = "push"
    RECOVERY = "recovery"


class SegmentDerivation(str, PyEnum):
    MANUAL = "manual"
    EVENT_DERIVED = "event_derived"
    MODEL_SUGGESTED = "model_suggested"


class ManualAnnotationSet(Base):
    """一套逻辑标注谱系（lineage）。

    仅承载归属与谱系信息，不保存可复现快照——快照全部在 revision 上。
    """

    __tablename__ = "manual_annotation_sets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    session_video_id: Mapped[int] = mapped_column(
        ForeignKey("session_videos.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # 新建 revision 时的默认 profile；revision 自身也保存 profile 快照。
    phase_profile_id: Mapped[str] = mapped_column(String(80), nullable=False)
    head_revision_id: Mapped[int | None] = mapped_column(
        ForeignKey("manual_annotation_revisions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    session_video = relationship("SessionVideo", back_populates="manual_annotation_sets")
    revisions = relationship(
        "ManualAnnotationRevision",
        back_populates="set",
        cascade="all, delete-orphan",
        foreign_keys="[ManualAnnotationRevision.set_id]",
    )


class ManualAnnotationRevision(Base):
    """某个时间点不可变（离开 draft 后）的标注内容版本。

    承载全部可复现快照：视频校验和、帧率/时长、frame mapping、phase profile 版本
    与 hash、内容 hash、状态与 provenance。分析任务通过 FK 显式引用本表。
    """

    __tablename__ = "manual_annotation_revisions"
    __table_args__ = (
        UniqueConstraint("set_id", "revision_no", name="uq_annotation_set_revision_no"),
        # 注意：MUST NOT 建立 UNIQUE(set_id, content_hash)。
        # fork 出来的 revision 内容必然与源相同，唯一约束会直接拒绝合法的
        # "标注员最终认为无需修改"场景。改为普通 index 由 1.4 建立。
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    set_id: Mapped[int] = mapped_column(
        ForeignKey("manual_annotation_sets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    revision_no: Mapped[int] = mapped_column(Integer, nullable=False)
    forked_from_revision_id: Mapped[int | None] = mapped_column(
        ForeignKey("manual_annotation_revisions.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # ── 可复现快照（快照时机 = 本 revision 发布时）──
    video_checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    video_fps_snapshot: Mapped[float | None] = mapped_column(Numeric(10, 4))
    video_duration_snapshot: Mapped[float | None] = mapped_column(Numeric(10, 3))
    frame_basis: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    phase_profile_id: Mapped[str] = mapped_column(String(80), nullable=False)
    phase_profile_version: Mapped[str] = mapped_column(String(40), nullable=False)
    phase_profile_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # content_hash：canonical JSON(segments) → sha256。
    # 见 services/reference_labels/hashing.py 的规范化规则。
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    status: Mapped[ManualRevisionStatus] = mapped_column(
        SQLEnum(ManualRevisionStatus, native_enum=False), default=ManualRevisionStatus.DRAFT, nullable=False, index=True
    )
    segment_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cycle_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # 乐观锁：draft 内容每次变更 edit_version 递增，写请求携带不匹配返回 409。
    edit_version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # provenance
    schema_version: Mapped[str] = mapped_column(String(40), nullable=False, default=SCHEMA_VERSION)
    created_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    updated_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reviewed_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    review_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    set = relationship(
        "ManualAnnotationSet",
        back_populates="revisions",
        foreign_keys=[set_id],
    )
    segments = relationship(
        "ManualPhaseSegment",
        back_populates="revision",
        cascade="all, delete-orphan",
        foreign_keys="[ManualPhaseSegment.revision_id]",
    )


class ManualPhaseSegment(Base):
    """一条人工时间区间标注（phase segment）。

    只通过 ``revision_id`` 归属，不冗余 ``set_id``。
    ``cycle_id`` 是跨 revision 稳定的逻辑周期标识。
    """

    __tablename__ = "manual_phase_segments"
    __table_args__ = (
        UniqueConstraint(
            "revision_id",
            "cycle_id",
            "side",
            "phase_code",
            name="uq_segment_revision_cycle_side_phase",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    revision_id: Mapped[int] = mapped_column(
        ForeignKey("manual_annotation_revisions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # 跨 revision 稳定的逻辑周期标识；fork 继承、新增才生成、删除后不复用。
    cycle_id: Mapped[str] = mapped_column(String(36), nullable=False)
    cycle_index: Mapped[int | None] = mapped_column(Integer, nullable=True)

    side: Mapped[SegmentSide] = mapped_column(SQLEnum(SegmentSide, native_enum=False), nullable=False)
    phase_code: Mapped[PhaseCode] = mapped_column(SQLEnum(PhaseCode, native_enum=False), nullable=False)

    # canonical source of truth
    start_time_sec: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)
    end_time_sec: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)
    # 派生快照（带 frame_basis），可 NULL
    start_frame: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_frame: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # 人工判据置信度（与 review_status 正交：reviewed ≠ confidence 1.0）。
    confidence: Mapped[float | None] = mapped_column(Numeric(4, 3), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    derivation: Mapped[SegmentDerivation] = mapped_column(
        SQLEnum(SegmentDerivation, native_enum=False), default=SegmentDerivation.MANUAL, nullable=False
    )

    schema_version: Mapped[str] = mapped_column(String(40), nullable=False, default=SCHEMA_VERSION)
    created_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    updated_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reviewed_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    review_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    revision = relationship("ManualAnnotationRevision", back_populates="segments", foreign_keys=[revision_id])
