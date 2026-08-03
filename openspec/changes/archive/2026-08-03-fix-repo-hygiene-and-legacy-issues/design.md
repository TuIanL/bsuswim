## Context

2026-08-03 全仓库体检确认：本地测试与前端构建均健康（515 passed、vue-tsc 通过），但存在 5 类工程卫生遗留问题。其中最关键的是 Alembic 迁移文件 `20260731_0016_add_report_interpretation_v3_catalog.py` 处于 untracked 状态——本地数据库已应用该迁移，但仓库中缺失此文件，任何新环境执行 `alembic upgrade head` 将停在 `20260730_0015`，而代码模型已引用 `reference_catalog` 列，应用启动即抛 `UndefinedColumn`。此外 49 个文件改动未提交、514 个运行产物被误纳入版本库、12 处弃用 API 告警等。

本 Change 属于纯工程卫生修复，不引入新功能，不改动运行时行为与数据模型语义（迁移文件只是纳入版本控制，不重复生成）。

## Goals / Non-Goals

**Goals:**
- 使仓库在新环境/CI 上可复现：`alembic upgrade head` 可达 head，应用可启动
- 消除未提交改动漂移：AI 报告解读 v3 catalog 相关改动按逻辑分组成为已提交基线
- 运行产物（`backend/uploads/` 下 SVG/PNG）移出版本控制，防止仓库膨胀与误删
- 消除 `datetime.utcnow()` 弃用告警，清理空壳/临时文件
- 通过 CI 检查固化卫生规则，防止问题回归

**Non-Goals:**
- 不实现 OpenSpec 变更 `add-kinematics-golden-dataset-e2e-validation` 的 E2E 收尾任务（另行处理）
- 不改变任何 API 契约、数据模型结构或业务逻辑
- 不做历史 git 历史改写（rebase/rewrite），仅增量提交
- 不删除磁盘上的运行产物文件（仅移出版本控制）

## Decisions

**D1: 迁移文件纳入版本控制，而非重新生成**
将现有 `20260731_0016_add_report_interpretation_v3_catalog.py` 原样 `git add`。
- 理由：文件内容正确（本地已验证 upgrade 到 head 后 schema 与模型一致），无需修改
- 备选：重新跑 `alembic revision` 生成新文件 —— 会引入重复迁移，拒绝

**D2: 未提交改动按 4 组提交**
- 组 1 迁移：`backend/alembic/versions/20260731_0016_*.py`
- 组 2 后端 v3 catalog：`backend/app/models/report.py`、`backend/app/schemas/report_interpretation.py`、`backend/app/services/report_interpretation/*`、`backend/app/core/config.py`、`backend/tests/test_report_interpretation.py`、`backend/tests/test_settings.py` 等
- 组 3 前端：`frontend-vue/src/components/report/AIInterpretationPanel.vue` 等组件与 `src/types.ts`、`src/utils/reportAdapter.ts`
- 组 4 文档/杂项：`docs/ai-report-interpretation-operations.md`、`.env.example`、synthetic contract fixture
- 理由：按逻辑边界分组便于回溯；不混入 E2E 收尾内容
- 备选：单一大提交 —— 回溯困难，拒绝

**D3: `backend/uploads/` 移出版本控制**
`.gitignore` 新增 `backend/uploads/`，对已跟踪的 514 个文件执行 `git rm --cached`（保留磁盘文件）。根目录 `uploads/*` 规则不变。
- 理由：运行产物（SVG 图表、关键帧 PNG）是每次分析动态生成的，不该进版本库；且此前工作区已出现删除态，说明产物变动正污染 diff
- 注意：`git rm --cached` 不会删除磁盘文件，但会让文件在 git 中表现为删除——提交后其他协作者 pull 时本地这些文件会被删除（可用 `git checkout` 恢复，或接受产物由运行时重建）
- 备选：仅加 gitignore 不动已跟踪文件 —— 已跟踪文件不受 gitignore 影响，问题依旧，拒绝

**D4: `datetime.utcnow()` 替换为 timezone-aware**
全仓 12 处 `datetime.utcnow()` → `datetime.now(timezone.utc)`（或 `datetime.now(UTC)`，Python 3.13 支持 `datetime.UTC`）。
- 理由：`utcnow()` 自 Python 3.12 弃用，3.13 产生 DeprecationWarning；返回值是 naive datetime，写入 DB 时与 aware datetime 混用有隐患
- 备选：仅抑制告警 —— 治标不治本，拒绝
- 注意：需确认所有消费方对 naive/aware 的假设；PostgreSQL `TIMESTAMP WITH TIME ZONE` 列兼容 aware datetime

**D5: 清理空壳与临时文件**
删除 `frontend/`（仅剩 node_modules，旧前端 `2026-07-14-remove-obsolete-next-frontend` 已归档）、工作区空日志（`.qwen-interpretation-304.log` 等 0 字节文件）。`.gitignore` 已含 `frontend/node_modules/`，删除后目录整体可移除。

**D6: CI 卫生检查**
在 `.github/workflows/ci.yml` 增加两步：迁移文件全部被 git 跟踪（`git ls-files --error-unmatch` 校验 head 迁移）；`git ls-files backend/uploads` 数量为 0。
- 理由：以 CI 失败固化规则，防止回归
- 备选：不加 CI 检查 —— 问题易复发，拒绝（实现时若 CI 环境不便可降级为本地脚本，作为任务开放项）

## Risks / Trade-offs

- [协作者 pull 后本地 `backend/uploads` 产物被删除] → 产物可由运行时重建；必要时 `git checkout -- backend/uploads` 恢复；文档说明
- [v3 catalog 未提交改动中混入未完成代码] → 提交前逐组运行 `pytest`（515 用例）与 `vue-tsc` 验证全绿再提交
- [utcnow 替换引入 naive/aware 行为变化] → 替换后跑全量测试 + 冒烟启动验证；DB 层为 aware 兼容
- [删除 `frontend/` 后若还有引用] → 该目录只剩 node_modules，无源码引用（旧前端已归档），删除安全
- [CI 检查在非 git 环境下误报] → 检查限定在已 checkout 的 CI job 中执行

## Migration Plan

1. 提交顺序：先提交迁移文件组（组 1），再后端组（组 2），再前端组（组 3），再文档组（组 4）
2. 每组提交前运行对应测试；全部提交后运行全量 `pytest` + `vue-tsc --noEmit` 最终验证
3. 执行 `git rm --cached` 提交产物移出；`frontend/` 与空日志删除并入组 4 或独立提交
4. 替换 utcnow 后运行全量测试
5. CI 卫生检查步骤提交后推送验证（若可推送）
6. 回滚策略：均为增量提交，任意一步出错用 `git revert` 或 `git reset` 回退对应提交，不影响其他提交

## Open Questions

- CI 卫生检查步骤是否需要纳入（取决于仓库是否立即推送 CI 触发）——由任务实现时确认
- `frontend/` 目录是否允许直接 `rm -rf`（涉及个人目录操作需用户确认，按文件安全规则走）
