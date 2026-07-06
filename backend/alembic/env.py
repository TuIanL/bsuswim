# ============================================================
# Alembic 迁移环境配置文件
# ------------------------------------------------------------
# 这个文件是 Alembic（数据库迁移工具）的“总控制台”。
# 当你在命令行执行 `alembic upgrade head` 或 `alembic downgrade` 时，
# Alembic 就会运行本文件，决定“用什么方式、连接哪个数据库、执行哪些迁移脚本”。
#
# 一句话：env.py 负责“搭桥”——把项目里的数据库配置和 versions/ 下的迁移脚本连接起来。
# ============================================================

# 从 Python 标准库读取日志配置（用于终端打印迁移过程的日志）
from logging.config import fileConfig

# Alembic 的核心：context 提供了访问配置和数据库连接的入口
from alembic import context
# SQLAlchemy 工具：用来根据配置创建数据库引擎（连接池）
from sqlalchemy import engine_from_config, pool

# 引入项目的配置对象，从中读取真实的数据库连接地址（DATABASE_URL）
from app.core.config import get_settings
# 引入 SQLAlchemy 的 Base，所有数据库表的“模型定义”都挂在 Base.metadata 上
from app.db.session import Base
# 导入所有模型模块（models 包），确保下面 target_metadata 能收集到全部表结构
# "noqa: F401" 告诉代码检查工具：这一行虽然没直接用，但导入它是有意的（不能删）
from app import models  # noqa: F401

# 读取 alembic.ini 中的配置
config = context.config

# 如果 ini 文件里配置了日志，就按它初始化日志系统
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# target_metadata：Alembic 做“自动对比数据库差异”时用到的表结构蓝图。
# 它来自 app.db.session.Base.metadata，也就是你所有 models 里定义的表。
target_metadata = Base.metadata

# 关键：用项目真实配置里的数据库地址，覆盖 ini 文件里占位用的 sqlalchemy.url。
# 这样你改 .env 里的 DATABASE_URL，迁移就会连到对应的库，无需改 ini 文件。
config.set_main_option("sqlalchemy.url", get_settings().database_url)


# ------------------------------------------------------------
# 离线迁移模式（offline / --sql）
# ------------------------------------------------------------
# “离线”指不真正连数据库，而是生成一串可执行的 SQL 语句（写进文件或打印）。
# 常用于：你不能直接连生产库，但可以把生成的 SQL 交给 DBA 去执行。
def run_migrations_offline() -> None:
    # 取出数据库连接地址
    url = config.get_main_option("sqlalchemy.url")
    # 配置迁移上下文：
    # - url：连哪个库
    # - target_metadata：表结构蓝图（离线模式主要靠它生成 SQL）
    # - literal_binds=True：把参数直接写进 SQL（而不是用占位符 ?）
    # - dialect_opts：指定 SQL 方言的参数风格
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    # 在一个事务里运行所有迁移脚本
    with context.begin_transaction():
        context.run_migrations()


# ------------------------------------------------------------
# 在线迁移模式（online，最常用）
# ------------------------------------------------------------
# “在线”指 Alembic 直接连上数据库，真正执行建表/改表操作。
def run_migrations_online() -> None:
    # 根据配置创建数据库引擎（连接对象）
    # - prefix="sqlalchemy."：从配置里取以 sqlalchemy. 开头的项（如 sqlalchemy.url）
    # - poolclass=pool.NullPool：迁移是一次性短任务，不需要连接池，用完即关
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    # 真正建立连接，并在该连接上配置迁移上下文，然后执行迁移
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


# ------------------------------------------------------------
# 入口：根据当前模式选择执行离线还是在线迁移
# ------------------------------------------------------------
# Alembic 会自动判断你是离线（--sql）还是在线模式
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
