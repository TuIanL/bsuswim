# ============================================================
# 迁移脚本 0002：新增标注文件表 annotation_files
# ============================================================
# 作用：在 0001（核心表）之后，新增“标注文件”相关功能。
# 这是迁移链的第二环：down_revision 指向 0001，表示它紧接在 0001 之后执行。
#
# 新增内容：
#   - 两个枚举：annotation_source（标注来源）、annotation_file_status（文件状态）
#   - 一张表：annotation_files（外部标注软件导出的文件，如 Kinovea/Dartfish）
#
# 背景：系统需要把教练用专业软件做的动作标注（如关节点轨迹）导入并解析，
#       这张表记录每个上传的标注文件及其解析状态。
# ============================================================

# 文件文档头：说明本次迁移内容、版本号、基于哪个旧版本（0001）、创建时间
"""add annotation_files table

Revision ID: 20260706_0002
Revises: 20260616_0001
Create Date: 2026-07-06
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# 迁移版本链：本版本号，以及它的“前任”是 0001
revision: str = "20260706_0002"
down_revision: Union[str, None] = "20260616_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# 标注来源枚举：来自哪款软件/方式
#   kinovea：Kinovea 视频分析软件；dartfish：Dartfish；manual_json：手写的 JSON；
#   ai_pose：AI 姿态估计生成；unknown：未知
annotation_source = postgresql.ENUM(
    "kinovea", "dartfish", "manual_json", "ai_pose", "unknown",
    name="annotationsource",
    create_type=False,
)
# 标注文件状态：已上传 / 已解析 / 解析失败 / 已归档
annotation_file_status = postgresql.ENUM(
    "uploaded", "parsed", "parse_failed", "archived",
    name="annotationfilestatus",
    create_type=False,
)


# ============================================================
# 升级：创建枚举 + 创建标注文件表
# ============================================================
def upgrade() -> None:
    bind = op.get_bind()
    annotation_source.create(bind, checkfirst=True)
    annotation_file_status.create(bind, checkfirst=True)

    # ---- 标注文件表 annotation_files：记录一份外部标注文件 ----
    op.create_table(
        "annotation_files",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_video_id", sa.Integer(), nullable=False),     # 关联 session_videos.id（属于哪段训练视频）
        sa.Column("source", annotation_source, nullable=False),          # 标注来源，用枚举
        sa.Column("original_filename", sa.String(length=255), nullable=False),  # 原始文件名
        sa.Column("stored_filename", sa.String(length=255), nullable=False),    # 系统存储文件名
        sa.Column("storage_path", sa.Text(), nullable=False),            # 存储路径（Text 可更长）
        sa.Column("file_type", sa.String(length=50), nullable=True),     # 文件类型（如 .xml/.json）
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),    # 文件大小（BigInteger 支持大文件）
        sa.Column("checksum_sha256", sa.String(length=64), nullable=True),     # 校验和
        sa.Column("annotation_fps", sa.Numeric(precision=8, scale=3), nullable=True),  # 标注帧率
        sa.Column("frame_count", sa.Integer(), nullable=True),           # 帧数
        sa.Column("duration_sec", sa.Numeric(precision=10, scale=3), nullable=True),  # 时长（秒）
        sa.Column("version", sa.Integer(), nullable=False),              # 版本号（同一视频可有多版标注）
        sa.Column("status", annotation_file_status, nullable=False),     # 文件状态，用枚举
        sa.Column("parse_error", sa.Text(), nullable=True),              # 解析失败时的错误信息
        sa.Column("uploaded_by", sa.Integer(), nullable=True),           # 上传者（关联 users.id）
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),  # 上传时间
        # JSONB 是 PostgreSQL 的“二进制 JSON”，查询/索引比普通 JSON 更快
        # server_default='{}'::jsonb 表示默认为空 JSON 对象
        sa.Column("metadata", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        # 外键：session_video_id → session_videos.id；ondelete="CASCADE" 表示若关联视频被删，本文件也跟着删
        sa.ForeignKeyConstraint(["session_video_id"], ["session_videos.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        # 同一训练视频 + 同一来源 + 同一版本，只能有一条（避免重复上传）
        sa.UniqueConstraint("session_video_id", "source", "version", name="uq_annotation_file_session_video_source_version"),
    )
    op.create_index(op.f("ix_annotation_files_id"), "annotation_files", ["id"], unique=False)
    op.create_index("ix_annotation_files_session_video", "annotation_files", ["session_video_id"], unique=False)
    op.create_index(op.f("ix_annotation_files_status"), "annotation_files", ["status"], unique=False)
    op.create_index("ix_annotation_files_source", "annotation_files", ["source"], unique=False)


# ============================================================
# 降级：删索引、删表、删枚举（顺序与升级相反）
# ============================================================
def downgrade() -> None:
    op.drop_index("ix_annotation_files_source", table_name="annotation_files")
    op.drop_index(op.f("ix_annotation_files_status"), table_name="annotation_files")
    op.drop_index("ix_annotation_files_session_video", table_name="annotation_files")
    op.drop_index(op.f("ix_annotation_files_id"), table_name="annotation_files")
    op.drop_table("annotation_files")

    bind = op.get_bind()
    annotation_file_status.drop(bind, checkfirst=True)
    annotation_source.drop(bind, checkfirst=True)
