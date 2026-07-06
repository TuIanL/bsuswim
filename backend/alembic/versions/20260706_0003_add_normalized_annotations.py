# ============================================================
# 迁移脚本 0003：新增归一化标注表 normalized_annotations
# ============================================================
# 作用：在 0002（标注文件）之后，新增“归一化标注”表。
# 这是迁移链的第三环：down_revision 指向 0002。
#
# 背景：不同来源（Kinovea / Dartfish / AI）的标注格式各不相同。
#   “归一化”就是把它们统一成一套标准结构（事件、关键点、轨迹、标签等），
#   方便系统统一存储和前端统一展示。这张表就存“统一后”的标注。
#
# 注意：本表没有新增枚举，全部用普通类型 + JSONB 存储灵活结构。
# ============================================================

# 文件文档头：说明本次迁移内容、版本号、基于哪个旧版本（0002）、创建时间
"""add normalized_annotations table

Revision ID: 20260706_0003
Revises: 20260706_0002
Create Date: 2026-07-06
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# 迁移版本链：本版本号，前任是 0002
revision: str = "20260706_0003"
down_revision: Union[str, None] = "20260706_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ============================================================
# 升级：创建归一化标注表
# ============================================================
def upgrade() -> None:
    op.create_table(
        "normalized_annotations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_video_id", sa.Integer(), nullable=False),      # 关联训练视频（session_videos.id）
        # 关联的“原始标注文件”id（来自 annotation_files）。可空：也可直接由 AI 生成、不依赖文件
        sa.Column("annotation_file_id", sa.Integer(), nullable=True),
        # 版本号，默认 1：同一视频可保存多版归一化标注
        sa.Column("revision", sa.Integer(), nullable=False, server_default=sa.text("1")),
        # 数据结构版本，默认 'swim-annotation.v1'：便于以后升级结构时兼容旧数据
        sa.Column("schema_version", sa.String(length=50), nullable=False, server_default=sa.text("'swim-annotation.v1'")),
        sa.Column("source", sa.String(length=50), nullable=False),        # 来源标识（如 kinovea / ai_pose）
        sa.Column("fps", sa.Numeric(precision=8, scale=3), nullable=False),  # 帧率
        sa.Column("frame_count", sa.Integer(), nullable=True),            # 帧数
        sa.Column("duration_sec", sa.Numeric(precision=10, scale=3), nullable=True),  # 时长（秒）
        # JSONB 字段：灵活存储各类结构化数据
        sa.Column("scale", postgresql.JSONB(), nullable=True),            # 比例尺信息（像素↔真实尺寸换算）
        sa.Column("coordinate_system", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),  # 坐标系定义
        sa.Column("events", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),            # 事件序列（如触壁、转身）
        sa.Column("keypoint_frames", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),   # 逐帧关键点
        sa.Column("trajectories", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),      # 关键点轨迹
        sa.Column("manual_tags", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),       # 人工标签
        # 数据质量：默认 {"level": "error"}，表示未校验；解析后会更新为 ok/warning 等
        sa.Column("quality", postgresql.JSONB(), server_default=sa.text("'{\"level\": \"error\"}'::jsonb"), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),          # 其他元数据
        sa.Column("created_by", sa.Integer(), nullable=True),             # 创建者（users.id）
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        # 外键：
        #   session_video_id → session_videos.id（CASCADE：视频删则标注删）
        #   annotation_file_id → annotation_files.id（SET NULL：文件删则置空，不连带删标注）
        #   created_by → users.id
        sa.ForeignKeyConstraint(["session_video_id"], ["session_videos.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["annotation_file_id"], ["annotation_files.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        # 一个原始标注文件只对应一份归一化标注（避免重复）
        sa.UniqueConstraint("annotation_file_id", name="uq_normalized_annotation_file"),
    )
    op.create_index(op.f("ix_normalized_annotations_id"), "normalized_annotations", ["id"], unique=False)
    op.create_index("ix_normalized_annotations_session_video", "normalized_annotations", ["session_video_id"], unique=False)
    op.create_index("ix_normalized_annotations_annotation_file", "normalized_annotations", ["annotation_file_id"], unique=False)


# ============================================================
# 降级：删索引、删表（无枚举要删）
# ============================================================
def downgrade() -> None:
    op.drop_index("ix_normalized_annotations_annotation_file", table_name="normalized_annotations")
    op.drop_index("ix_normalized_annotations_session_video", table_name="normalized_annotations")
    op.drop_index(op.f("ix_normalized_annotations_id"), table_name="normalized_annotations")
    op.drop_table("normalized_annotations")
