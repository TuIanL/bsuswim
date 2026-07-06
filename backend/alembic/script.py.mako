# ============================================================
# Alembic 迁移脚本模板（script.py.mako）
# ------------------------------------------------------------
# 这是“生成新迁移文件”的模板。你平时不用直接改它，
# 但了解它有助于读懂 versions/ 下每个迁移文件的来历与结构。
#
# 当你执行 `alembic revision -m "改了什么"` 时，Alembic 会复制本模板，
# 并把里面 ${...} 的占位符替换成真实值，生成一个新的 .py 迁移文件。
#
# 注意：本文件是“模板”，不是被执行的迁移；真正执行的是 versions/ 下的 .py。
# ============================================================

# 文件最上方的三引号字符串是迁移文件的“文档头”（docstring），
# Alembic 把本次修改说明、版本号、基于哪个旧版本、创建时间填进来。
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}
"""

# 类型注解用：Sequence（序列/列表）、Union（联合类型）
from typing import Sequence, Union

# op：Alembic 提供的“操作工具箱”，用来建表/加列/建索引等
from alembic import op
# sa：SQLAlchemy 核心，用来描述列类型（Integer、String 等）
import sqlalchemy as sa
# 如果迁移中用到了额外 import（比如自定义类型），Alembic 会把它们填到这里
${imports if imports else ""}

# 本次迁移的版本号（唯一 ID）。Alembic 用它串起迁移链。
revision: str = ${repr(up_revision)}
# 上一次迁移的版本号（指向谁）。None 表示这是第一条迁移。
# 这就是“版本链”：down_revision 指向上一个，Alembic 据此知道执行顺序。
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


# 升级函数：执行 `alembic upgrade` 时调用，把数据库“向前”改到新结构
def upgrade() -> None:
    # 模板里若有具体升级语句会替换 ${upgrades}，否则默认 pass（什么都不做）
    ${upgrades if upgrades else "pass"}


# 降级函数：执行 `alembic downgrade` 时调用，把数据库“退回”到旧结构
def downgrade() -> None:
    # 与 upgrade 相反，用于回滚本次变更
    ${downgrades if downgrades else "pass"}
