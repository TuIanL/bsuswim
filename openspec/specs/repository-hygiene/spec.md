# Capability: repository-hygiene

## Purpose

定义仓库卫生契约，确保 Alembic 迁移文件被版本控制、运行产物不进入版本库、代码不使用已弃用的标准库 API、空壳与临时文件及时清理，并通过 CI 固化检查防止回归。

## Requirements

### Requirement: Alembic 迁移文件必须被版本控制

仓库中所有 Alembic 迁移文件 SHALL 被 git 跟踪。当前 head 迁移 `20260731_0016_add_report_interpretation_v3_catalog.py` 必须纳入版本控制，确保任何新环境执行 `alembic upgrade head` 可达 head 且应用可正常启动。

#### Scenario: 新环境执行迁移

- **WHEN** 协作者在新环境 clone 仓库并运行 `alembic upgrade head`
- **THEN** 迁移成功到达 head revision `20260731_0016`，且 `report_interpretations.reference_catalog` 列存在，应用可正常启动

#### Scenario: 迁移文件完整性检查

- **WHEN** 执行 `git ls-files backend/alembic/versions/` 校验 head 迁移文件
- **THEN** `20260731_0016_add_report_interpretation_v3_catalog.py` 出现在跟踪列表中

### Requirement: 运行产物不得进入版本库

`backend/uploads/` 目录下的动态运行产物（SVG 图表、关键帧 PNG 等）SHALL 不被 git 跟踪。`backend/uploads/` SHALL 加入 `.gitignore`，已跟踪的产物文件 SHALL 通过 `git rm --cached` 移出版本控制（不删除磁盘文件）。

#### Scenario: 产物移出版本控制

- **WHEN** 执行 `git rm --cached -r backend/uploads/` 并提交
- **THEN** `git ls-files backend/uploads` 返回 0 个文件，磁盘上的产物文件仍然存在

#### Scenario: 新产物不再被跟踪

- **WHEN** 系统运行分析任务生成新的 SVG/PNG 产物到 `backend/uploads/`
- **THEN** `git status` 不显示这些新产物为待跟踪文件

### Requirement: 不使用已弃用的标准库 API

后端代码 SHALL 不调用已弃用的 `datetime.datetime.utcnow()`。代码 SHALL 使用 timezone-aware 的 `datetime.datetime.now(timezone.utc)`（或 `datetime.UTC`）替代。

#### Scenario: 全仓无 utcnow 调用

- **WHEN** 执行 `grep -rn "utcnow()" backend/app --include="*.py"`
- **THEN** 无任何匹配结果

#### Scenario: 时间戳保持 UTC aware

- **WHEN** 服务写入 `completed_at`、`generated_at` 等时间字段
- **THEN** 写入的是带 UTC 时区信息的 aware datetime，测试无 DeprecationWarning

### Requirement: 空壳与临时文件及时清理

仓库中已废弃的空壳目录（如 `frontend/`，仅剩 node_modules）与工作区空日志文件 SHALL 被清理，不再存在于磁盘与版本库中。

#### Scenario: 空壳目录清理

- **WHEN** 检查 `frontend/` 目录
- **THEN** 目录不存在（旧前端已归档，仅剩的 node_modules 一并移除）

#### Scenario: 空日志清理

- **WHEN** 检查工作区根目录的 0 字节日志文件（如 `.qwen-interpretation-304.log`）
- **THEN** 文件不存在

### Requirement: CI 校验仓库卫生

CI 工作流 SHALL 包含仓库卫生检查步骤：迁移文件全部被 git 跟踪；`backend/uploads` 无任何被跟踪文件。

#### Scenario: CI 卫生检查通过

- **WHEN** CI 在干净 checkout 上执行卫生检查命令
- **THEN** head 迁移文件在 git 跟踪列表中，且 `git ls-files backend/uploads` 为空，CI 步骤成功

#### Scenario: CI 卫生检查失败

- **WHEN** 有新的迁移文件未被 git 跟踪，或有产物被跟踪进入 `backend/uploads`
- **THEN** CI 对应步骤失败，阻断合并
