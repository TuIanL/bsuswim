"""人工参考标注 API schema（读写 DTO）。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class FrameBasis(BaseModel):
    fps: float | None = None
    fps_source: str | None = None
    mapping_mode: str | None = None
    mapping_verified: bool = False


class SetCreate(BaseModel):
    phase_profile_id: str


class SetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_video_id: int
    phase_profile_id: str
    head_revision_id: int | None
    created_by: int | None
    created_at: datetime
    updated_at: datetime


class RevisionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    set_id: int
    revision_no: int
    forked_from_revision_id: int | None
    video_checksum_sha256: str
    video_fps_snapshot: float | None = None
    video_duration_snapshot: float | None = None
    frame_basis: dict | None = None
    phase_profile_id: str
    phase_profile_version: str
    phase_profile_hash: str
    content_hash: str
    status: str
    segment_count: int
    cycle_count: int
    edit_version: int
    created_by: int | None
    updated_by: int | None
    reviewed_by: int | None
    review_status: str | None
    reviewed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class SegmentCreate(BaseModel):
    cycle_id: str
    side: str
    phase_code: str
    start_time_sec: float
    end_time_sec: float
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    note: str | None = None
    edit_version: int


class SegmentUpdate(BaseModel):
    cycle_id: str | None = None
    side: str | None = None
    phase_code: str | None = None
    start_time_sec: float | None = None
    end_time_sec: float | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    note: str | None = None
    edit_version: int


class SegmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    revision_id: int
    cycle_id: str
    cycle_index: int | None
    side: str
    phase_code: str
    start_time_sec: float
    end_time_sec: float
    start_frame: int | None
    end_frame: int | None
    confidence: float | None
    note: str | None
    derivation: str
    created_by: int | None
    updated_by: int | None
    reviewed_by: int | None
    review_status: str | None
    created_at: datetime
    updated_at: datetime


class PhaseDefRead(BaseModel):
    code: str
    display: str
    start: str
    end: str


class BoundaryDefRead(BaseModel):
    name: str
    display: str
    operational_definition: str
    reference_joint: str
    annotation_guidance: str


class PhaseProfileRead(BaseModel):
    id: str
    version: str
    cycle_partition_by: str
    cycle_boundary: str
    phases: list[PhaseDefRead]
    required_boundaries: list[str]
    optional_boundaries: list[str]
    boundary_definitions: dict[str, BoundaryDefRead]


class ForkResponse(BaseModel):
    id: int
    set_id: int
    revision_no: int
    forked_from_revision_id: int | None
    status: str
