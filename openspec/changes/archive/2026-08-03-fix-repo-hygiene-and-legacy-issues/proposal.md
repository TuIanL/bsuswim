## Why

2026-08-03 全仓库体检发现若干历史遗留问题：Alembic 迁移文件 `20260731_0016` 未被 git 跟踪（新环境/CI 执行 `alembic upgrade head` 只会停在 0015，而代码已引用 `reference_catalog` 列，应用启动必然抛 `UndefinedColumn`——7/31 开发日志中的报错正是此问题的历史现场）；AI 报告解读 v3 catalog 的 49 个文件改动（+1494/−20897 行）处于未提交的半成品状态；514 个运行产物（SVG/PNG）被误纳入版本库且部分已删除；另存在 12 处 `datetime.utcnow()` 弃用告警、`frontend/` 空壳目录、空日志文件等卫生问题。这些不影响当前本地测试（515 通过），但会阻断任何新环境部署与协作提交，需在继续 E2E 收尾之前修复。

## What Changes

- **纳入迁移文件到版本控制**：`backend/alembic/versions/20260731_0016_add_report_interpretation_v3_catalog.py` 加入 git 跟踪，保证新环境 `alembic upgrade head` 可达 head，消除启动即失败的隐患
- **提交 AI 报告解读 v3 catalog 未完成改动**：按逻辑分组（迁移 + 后端模型/schema/service + 前端组件 + 文档 + 测试）提交当前未提交改动，使工作区与仓库一致；不含 E2E 收尾内容
- **运行产物移出版本库**：`backend/uploads/` 加入 `.gitignore`，已跟踪的 514 个产物文件 `git rm --cached` 移出版本控制（保留磁盘文件）；根目录 `uploads/*` 规则保持不变
- **清理空壳与临时文件**：删除 `frontend/` 空壳目录（仅剩 node_modules，旧前端已归档）、工作区空日志文件（`.qwen-interpretation-304.log` 等）
- **消除弃用告警**：将 12 处 `datetime.utcnow()` 替换为 timezone-aware 的 `datetime.now(UTC)`，消除 Python 3.13 弃用告警
- **CI 增加仓库卫生检查**（可选，纳入 tasks 由实现时确认）：验证迁移文件全部被 git 跟踪、`backend/uploads/` 无新增跟踪产物

## Capabilities

### New Capabilities

- `repository-hygiene`: 定义仓库卫生契约——所有 Alembic 迁移文件 SHALL 被版本控制；运行产物目录 SHALL 不进入版本库；代码 SHALL 不使用已弃用的标准库 API；空壳/临时文件 SHALL 及时清理

### Modified Capabilities

无——本 Change 不改变任何已定义能力的需求行为（未提交的 v3 catalog 改动是既有已实现行为的落库提交，无 spec 级变更）

## Impact

- `backend/alembic/versions/20260731_0016_add_report_interpretation_v3_catalog.py`：纳入 git 跟踪
- `backend/app/models/report.py`、`backend/app/schemas/report_interpretation.py`、`backend/app/services/report_interpretation/*`、`backend/app/core/config.py`、`backend/tests/test_report_interpretation.py` 等 49 个未提交文件：分组提交
- `frontend-vue/src/`：AIInterpretationPanel 等前端组件改动随提交
- `.gitignore`：新增 `backend/uploads/`
- `backend/uploads/`：514 个文件 `git rm --cached`（磁盘保留）
- `backend/app/`：12 处 `datetime.utcnow()` → `datetime.now(UTC)`
- `frontend/`：删除空壳目录
- `.qwen-interpretation-304.log` 等空日志：清理
