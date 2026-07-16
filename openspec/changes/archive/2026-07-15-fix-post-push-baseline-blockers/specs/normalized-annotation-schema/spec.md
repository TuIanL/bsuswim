## MODIFIED Requirements

### Requirement: Source enum includes cvat

系统 SHALL 扩展 `AnnotationSource` 枚举，增加 `cvat` 为有效来源值。**PostgreSQL 数据库中的 `annotationsource` 枚举类型 SHALL 同时通过 ALTER TYPE 语句增加 `cvat` 值，确保 ORM 写入不报错。**

#### Scenario: Valid source values include cvat

- **WHEN** 创建或更新 normalized annotation 时提供 `source = "cvat"`
- **THEN** 系统 MUST 接受 `cvat` 作为有效值
- **THEN** PostgreSQL 层 MUST 不因 ENUM 值不存在而报 `invalid input value for enum` 错误

#### Scenario: PostgreSQL enum updated by migration

- **WHEN** 开发者执行新增 migration
- **THEN** `ALTER TYPE annotationsource ADD VALUE IF NOT EXISTS 'cvat'` MUST 成功执行
- **THEN** `SELECT unnest(enum_range(NULL::annotationsource))` 结果 MUST 包含 `cvat`

#### Scenario: Downgrade is no-op

- **WHEN** 开发者执行 `alembic downgrade -1`
- **THEN** migration 的 downgrade MUST 不报错（PostgreSQL 不支持安全移除 enum value）

## ADDED Requirements

### Requirement: Unique constraint alignment

SQLAlchemy model 的约束定义 SHALL 与 Alembic migration 中的约束定义一致，避免 `alembic check` 报漂移。

#### Scenario: NormalizedAnnotation no duplicate unique

- **WHEN** `NormalizedAnnotation` ORM 模型定义中 `annotation_file_id` 列同时有 `unique=True` 和 `__table_args__` 中的 `UniqueConstraint`
- **THEN** 系统 MUST 删除列上的 `unique=True`，保留 `__table_args__` 中的命名唯一约束

#### Scenario: AnnotationMetric has model-level unique constraint

- **WHEN** `AnnotationMetric` ORM 模型定义
- **THEN** 系统 MUST 在 `__table_args__` 中声明 `UniqueConstraint("normalized_annotation_id", "calculator", "calculator_version", name="uq_annotation_metrics_calc")`
