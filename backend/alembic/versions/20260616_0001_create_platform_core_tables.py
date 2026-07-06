# ============================================================
# 迁移脚本 0001：创建平台核心数据表（第一条迁移，基础骨架）
# ============================================================
# 作用：首次搭建数据库时执行，创建整个系统的核心表和基础枚举类型。
# 这是迁移链的第一环（down_revision = None 表示它是起点）。
# 本文件 revision = "20260616_0001"，执行顺序排在最前。
#
# 涉及的表：
#   users（用户）、teams（队伍）、video_files（上传的视频文件）
#   athletes（运动员）、training_sessions（训练记录）、session_videos（记录-视频关联）
#   analysis_tasks（分析任务）、analysis_results（分析结果）、report_metadata（报告）
#
# 涉及的枚举（ENUM，即“只能取固定几个值”的列类型）：
#   analysis_task_status、stroke_type、training_session_status、user_role、view_type
# ============================================================

# 文件文档头：说明本次迁移内容、版本号、基于哪个旧版本（无）、创建时间
"""create platform core tables

Revision ID: 20260616_0001
Revises:
Create Date: 2026-06-16
"""
# 类型注解：Sequence（序列/列表）、Union（可以是多种类型之一）
from typing import Sequence, Union

# op：Alembic 操作工具，建表/加列/建索引等都通过它
from alembic import op
# sa：SQLAlchemy 核心，描述列类型（Integer、String、DateTime 等）
import sqlalchemy as sa
# postgresql：PostgreSQL 专属类型，这里用来定义枚举（ENUM）
from sqlalchemy.dialects import postgresql


# ---- 迁移版本链信息（不要随意改动，否则 Alembic 找不到顺序） ----
# 本次迁移的唯一版本号
revision: str = "20260616_0001"
# 上一条迁移：None 表示这是第一条，没有前身
down_revision: Union[str, None] = None
# 分支标签 / 依赖（本项目未用，均为 None）
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ============================================================
# 枚举类型（ENUM）定义
# ------------------------------------------------------------
# ENUM = 一列的值只能从给定清单里选，写错值数据库会报错。
# 这些类型在升级时创建、降级时删除。
# create_type=False 表示：这里的对象只是“类型描述”，真正建库的动作在 upgrade 里手动 .create()。
# ============================================================

# 分析任务的状态：上传完成 / 排队中 / 处理中 / 结果保存中 / 已完成 / 失败
analysis_task_status = postgresql.ENUM(
    "UPLOADED",
    "QUEUED",
    "PROCESSING",
    "RESULT_SAVING",
    "COMPLETED",
    "FAILED",
    name="analysistaskstatus",   # 在数据库里这个类型的名字（不要改，要和模型对应）
    create_type=False,
)

# 泳姿类型：自由泳 / 蛙泳 / 仰泳 / 蝶泳 / 混合泳
stroke_type = postgresql.ENUM(
    "FREESTYLE",
    "BREASTSTROKE",
    "BACKSTROKE",
    "BUTTERFLY",
    "MIXED",
    name="stroketype",
    create_type=False,
)

# 训练记录的状态：草稿 / 已上传视频 / 分析中 / 已完成 / 失败
training_session_status = postgresql.ENUM(
    "DRAFT",
    "VIDEO_UPLOADED",
    "ANALYZING",
    "COMPLETED",
    "FAILED",
    name="trainingsessionstatus",
    create_type=False,
)

# 用户角色：管理员 / 教练 / 运动员
user_role = postgresql.ENUM("ADMIN", "COACH", "ATHLETE", name="userrole", create_type=False)

# 视频拍摄视角：侧面 / 正面 / 俯视 / 水下 / 其他
view_type = postgresql.ENUM("SIDE", "FRONT", "TOP", "UNDERWATER", "OTHER", name="viewtype", create_type=False)


# ============================================================
# 升级：创建枚举 + 创建所有核心表
# ============================================================
def upgrade() -> None:
    # 拿到数据库实际连接（bind），用于创建/删除枚举类型
    bind = op.get_bind()
    # checkfirst=True：如果已存在就跳过，避免重复创建报错
    analysis_task_status.create(bind, checkfirst=True)
    stroke_type.create(bind, checkfirst=True)
    training_session_status.create(bind, checkfirst=True)
    user_role.create(bind, checkfirst=True)
    view_type.create(bind, checkfirst=True)

    # ---- 用户表 users：系统登录账号 ----
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),                       # 主键自增 ID
        sa.Column("username", sa.String(length=80), nullable=False),         # 用户名（登录用），不可为空
        sa.Column("email", sa.String(length=255), nullable=True),            # 邮箱（可空）
        sa.Column("phone", sa.String(length=30), nullable=True),             # 手机号（可空）
        sa.Column("password_hash", sa.String(length=255), nullable=False),   # 密码的哈希值（绝不存明文！）
        sa.Column("full_name", sa.String(length=80), nullable=True),         # 真实姓名（可空）
        sa.Column("role", user_role, nullable=False),                        # 角色，用上面定义的枚举
        sa.Column("is_active", sa.Boolean(), nullable=False),                # 是否启用（封禁用）
        # 创建时间 / 更新时间：默认取数据库当前时间 now()，带时区
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),   # id 设为主键
    )
    # 建索引：索引像书的目录，加速按这些列查询
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)   # 用户名唯一
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)         # 邮箱唯一
    op.create_index(op.f("ix_users_phone"), "users", ["phone"], unique=True)         # 手机号唯一

    # ---- 队伍表 teams：运动员/教练所属的团队 ----
    op.create_table(
        "teams",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),            # 队伍名称
        sa.Column("team_type", sa.String(length=40), nullable=True),         # 队伍类型（如校队/俱乐部）
        sa.Column("description", sa.Text(), nullable=True),                  # 简介（长文本）
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),   # 队伍名唯一，不能重名
    )
    op.create_index(op.f("ix_teams_id"), "teams", ["id"], unique=False)

    # ---- 视频文件表 video_files：用户上传的原始视频元数据 ----
    op.create_table(
        "video_files",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),  # 上传时的原始文件名
        sa.Column("stored_filename", sa.String(length=255), nullable=False),    # 系统存储用的文件名（一般带随机串）
        sa.Column("storage_path", sa.String(length=500), nullable=False),       # 服务器上的实际存储路径
        sa.Column("mime_type", sa.String(length=120), nullable=True),            # 文件类型，如 video/mp4
        sa.Column("size_bytes", sa.Integer(), nullable=False),                   # 文件大小（字节）
        sa.Column("checksum_sha256", sa.String(length=64), nullable=False),      # 校验和，用于查重/完整性校验
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stored_filename"),   # 存储文件名唯一
    )
    op.create_index(op.f("ix_video_files_id"), "video_files", ["id"], unique=False)

    # ---- 运动员表 athletes：被训练/分析的人 ----
    op.create_table(
        "athletes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),               # 姓名
        sa.Column("gender", sa.String(length=20), nullable=True),              # 性别（可空）
        sa.Column("birth_date", sa.Date(), nullable=True),                     # 出生日期
        sa.Column("height_cm", sa.Numeric(precision=5, scale=2), nullable=True),  # 身高 cm，定点数(共5位,2位小数)
        sa.Column("weight_kg", sa.Numeric(precision=5, scale=2), nullable=True),  # 体重 kg
        sa.Column("stroke_specialty", sa.String(length=40), nullable=True),    # 主攻泳姿
        sa.Column("level", sa.String(length=40), nullable=True),               # 水平等级（如 一级/二级）
        sa.Column("notes", sa.Text(), nullable=True),                          # 备注
        sa.Column("coach_id", sa.Integer(), nullable=True),                    # 主管教练（关联 users.id，可空）
        sa.Column("team_id", sa.Integer(), nullable=True),                     # 所属队伍（关联 teams.id，可空）
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        # 外键：coach_id → users.id；team_id → teams.id（保证引用的用户/队伍必须存在）
        sa.ForeignKeyConstraint(["coach_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_athletes_id"), "athletes", ["id"], unique=False)
    op.create_index(op.f("ix_athletes_coach_id"), "athletes", ["coach_id"], unique=False)
    op.create_index(op.f("ix_athletes_team_id"), "athletes", ["team_id"], unique=False)

    # ---- 训练记录表 training_sessions：一次训练课 ----
    op.create_table(
        "training_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("athlete_id", sa.Integer(), nullable=False),                 # 哪位运动员（关联 athletes.id）
        sa.Column("coach_id", sa.Integer(), nullable=True),                    # 教练（关联 users.id，可空）
        sa.Column("title", sa.String(length=120), nullable=False),             # 训练标题
        sa.Column("session_date", sa.Date(), nullable=True),                   # 训练日期
        sa.Column("venue", sa.String(length=120), nullable=True),              # 场馆
        sa.Column("stroke_type", stroke_type, nullable=False),                 # 泳姿，用枚举
        sa.Column("distance_m", sa.Integer(), nullable=True),                  # 距离（米）
        sa.Column("pool_length_m", sa.Numeric(precision=5, scale=2), nullable=True),  # 泳池长度（米）
        sa.Column("status", training_session_status, nullable=False),          # 状态，用枚举
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["athlete_id"], ["athletes.id"]),
        sa.ForeignKeyConstraint(["coach_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_training_sessions_id"), "training_sessions", ["id"], unique=False)
    op.create_index(op.f("ix_training_sessions_athlete_id"), "training_sessions", ["athlete_id"], unique=False)
    op.create_index(op.f("ix_training_sessions_coach_id"), "training_sessions", ["coach_id"], unique=False)
    op.create_index(op.f("ix_training_sessions_status"), "training_sessions", ["status"], unique=False)

    # ---- 记录-视频关联表 session_videos：一次训练可绑定多个视频（多机位） ----
    op.create_table(
        "session_videos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),                 # 关联 training_sessions.id
        sa.Column("video_file_id", sa.Integer(), nullable=False),              # 关联 video_files.id
        sa.Column("view_type", view_type, nullable=False),                     # 拍摄视角，用枚举
        sa.Column("fps", sa.Numeric(precision=6, scale=2), nullable=True),     # 帧率
        sa.Column("resolution", sa.String(length=40), nullable=True),          # 分辨率，如 1920x1080
        sa.Column("sync_offset_ms", sa.Integer(), nullable=False),             # 多机位时间同步偏移（毫秒）
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["training_sessions.id"]),
        sa.ForeignKeyConstraint(["video_file_id"], ["video_files.id"]),
        sa.PrimaryKeyConstraint("id"),
        # 同一训练下，同一个视频文件不能重复绑定（唯一约束）
        sa.UniqueConstraint("session_id", "video_file_id", name="uq_session_video_file"),
    )
    op.create_index(op.f("ix_session_videos_id"), "session_videos", ["id"], unique=False)
    op.create_index(op.f("ix_session_videos_session_id"), "session_videos", ["session_id"], unique=False)
    op.create_index(op.f("ix_session_videos_video_file_id"), "session_videos", ["video_file_id"], unique=False)

    # ---- 分析任务表 analysis_tasks：对一次训练发起的 AI 分析任务 ----
    op.create_table(
        "analysis_tasks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),                 # 关联训练记录
        sa.Column("status", analysis_task_status, nullable=False),             # 任务状态，用枚举
        sa.Column("progress", sa.Integer(), nullable=False),                   # 进度百分比 0~100
        sa.Column("stage", sa.String(length=80), nullable=False),              # 当前阶段描述（如 model_inference）
        sa.Column("request_payload", sa.JSON(), nullable=False),               # 发给模型服务的请求内容（JSON）
        sa.Column("error_message", sa.Text(), nullable=True),                  # 失败时的错误信息
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),  # 完成时间（可空，未完成则无）
        sa.ForeignKeyConstraint(["session_id"], ["training_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_analysis_tasks_id"), "analysis_tasks", ["id"], unique=False)
    op.create_index(op.f("ix_analysis_tasks_session_id"), "analysis_tasks", ["session_id"], unique=False)
    op.create_index(op.f("ix_analysis_tasks_status"), "analysis_tasks", ["status"], unique=False)

    # ---- 分析结果表 analysis_results：模型返回的结构化结果 ----
    op.create_table(
        "analysis_results",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=False),                    # 关联分析任务
        sa.Column("schema_version", sa.String(length=40), nullable=False),     # 结果数据结构版本号
        # 以下都是 JSON 类型，存模型输出的复杂结构（检测框/关键点/阶段/指标/诊断）
        sa.Column("detections", sa.JSON(), nullable=False),                    # 检测框
        sa.Column("keypoint_frames", sa.JSON(), nullable=False),               # 关键点逐帧数据
        sa.Column("phases", sa.JSON(), nullable=False),                        # 动作阶段划分
        sa.Column("metrics", sa.JSON(), nullable=False),                       # 技术指标
        sa.Column("diagnostics", sa.JSON(), nullable=False),                   # 诊断结论与建议
        sa.Column("raw_result", sa.JSON(), nullable=False),                    # 模型原始返回（完整备份）
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["analysis_tasks.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task_id"),   # 一个任务只对应一份结果
    )
    op.create_index(op.f("ix_analysis_results_id"), "analysis_results", ["id"], unique=False)

    # ---- 报告表 report_metadata：基于分析结果生成的训练报告 ----
    op.create_table(
        "report_metadata",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),                 # 关联训练记录
        sa.Column("task_id", sa.Integer(), nullable=False),                    # 关联分析任务
        sa.Column("source", sa.String(length=80), nullable=False),             # 报告来源（如 model_service_mock）
        sa.Column("report_data", sa.JSON(), nullable=False),                   # 报告渲染所需数据（JSON）
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),  # 生成时间
        sa.ForeignKeyConstraint(["session_id"], ["training_sessions.id"]),
        sa.ForeignKeyConstraint(["task_id"], ["analysis_tasks.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", name="uq_report_session"),           # 一次训练一份报告
        sa.UniqueConstraint("task_id"),
    )
    op.create_index(op.f("ix_report_metadata_id"), "report_metadata", ["id"], unique=False)
    op.create_index(op.f("ix_report_metadata_session_id"), "report_metadata", ["session_id"], unique=False)


# ============================================================
# 降级：按“建表的反顺序”删除所有表和枚举
# ------------------------------------------------------------
# 顺序很重要：先删子表（依赖别人的），再删父表（被依赖的）；
# 先删索引，再删表。否则会因外键约束报错。
# ============================================================
def downgrade() -> None:
    # 删 report_metadata 的索引与表
    op.drop_index(op.f("ix_report_metadata_session_id"), table_name="report_metadata")
    op.drop_index(op.f("ix_report_metadata_id"), table_name="report_metadata")
    op.drop_table("report_metadata")
    # 删 analysis_results
    op.drop_index(op.f("ix_analysis_results_id"), table_name="analysis_results")
    op.drop_table("analysis_results")
    # 删 analysis_tasks（含 3 个索引）
    op.drop_index(op.f("ix_analysis_tasks_status"), table_name="analysis_tasks")
    op.drop_index(op.f("ix_analysis_tasks_session_id"), table_name="analysis_tasks")
    op.drop_index(op.f("ix_analysis_tasks_id"), table_name="analysis_tasks")
    op.drop_table("analysis_tasks")
    # 删 session_videos
    op.drop_index(op.f("ix_session_videos_video_file_id"), table_name="session_videos")
    op.drop_index(op.f("ix_session_videos_session_id"), table_name="session_videos")
    op.drop_index(op.f("ix_session_videos_id"), table_name="session_videos")
    op.drop_table("session_videos")
    # 删 training_sessions
    op.drop_index(op.f("ix_training_sessions_status"), table_name="training_sessions")
    op.drop_index(op.f("ix_training_sessions_coach_id"), table_name="training_sessions")
    op.drop_index(op.f("ix_training_sessions_athlete_id"), table_name="training_sessions")
    op.drop_index(op.f("ix_training_sessions_id"), table_name="training_sessions")
    op.drop_table("training_sessions")
    # 删 athletes
    op.drop_index(op.f("ix_athletes_team_id"), table_name="athletes")
    op.drop_index(op.f("ix_athletes_coach_id"), table_name="athletes")
    op.drop_index(op.f("ix_athletes_id"), table_name="athletes")
    op.drop_table("athletes")
    # 删 video_files
    op.drop_index(op.f("ix_video_files_id"), table_name="video_files")
    op.drop_table("video_files")
    # 删 teams
    op.drop_index(op.f("ix_teams_id"), table_name="teams")
    op.drop_table("teams")
    # 删 users（含 4 个索引）
    op.drop_index(op.f("ix_users_phone"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_index(op.f("ix_users_id"), table_name="users")
    op.drop_table("users")

    # 最后删除枚举类型（与创建顺序相反）
    bind = op.get_bind()
    view_type.drop(bind, checkfirst=True)
    user_role.drop(bind, checkfirst=True)
    training_session_status.drop(bind, checkfirst=True)
    stroke_type.drop(bind, checkfirst=True)
    analysis_task_status.drop(bind, checkfirst=True)
