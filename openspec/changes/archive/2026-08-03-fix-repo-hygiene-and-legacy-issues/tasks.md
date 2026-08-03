## 1. 迁移文件纳入版本控制

- [x] 1.1 确认 `backend/alembic/versions/20260731_0016_add_report_interpretation_v3_catalog.py` 内容正确（revision/down_revision 与 upgrade/downgrade 逻辑无误）
- [x] 1.2 `git add backend/alembic/versions/20260731_0016_add_report_interpretation_v3_catalog.py` 并提交（组 1：迁移）
- [x] 1.3 验证 `git ls-files backend/alembic/versions/` 包含 0016 文件

## 2. 提交 AI 报告解读 v3 catalog 未完成改动

- [x] 2.1 运行全量后端测试 `pytest tests/ --ignore=tests/e2e` 确认提交前基线全绿（515 passed）
- [x] 2.2 运行前端类型检查 `vue-tsc --noEmit` 确认基线全绿
- [x] 2.3 提交后端组：`backend/app/models/report.py`、`backend/app/schemas/report_interpretation.py`、`backend/app/services/report_interpretation/*`、`backend/app/core/config.py`
- [x] 2.4 提交测试组：`backend/tests/test_report_interpretation.py`、`backend/tests/test_settings.py`、`backend/tests/fixtures/synthetic_five_page_report_contract.json`
- [x] 2.5 提交前端组：`frontend-vue/src/components/report/AIInterpretationPanel.vue`、`shared/*`、`src/types.ts`、`src/utils/reportAdapter.ts` 等改动文件及其 `.spec.ts`
- [x] 2.6 提交文档/杂项组：`docs/ai-report-interpretation-operations.md`、`.env.example`
- [x] 2.7 提交后复查 `git status` 确认无 v3 catalog 相关遗留未提交文件（新 untracked 产物除外）

## 3. 运行产物移出版本库

- [x] 3.1 `.gitignore` 新增 `backend/uploads/` 规则
- [x] 3.2 执行 `git rm --cached -r backend/uploads/`（保留磁盘文件）
- [x] 3.3 验证 `git ls-files backend/uploads` 返回 0，磁盘文件仍在
- [x] 3.4 提交产物移出变更，确认提交信息说明产物由运行时重建

## 4. 清理空壳与临时文件

- [x] 4.1 确认 `frontend/` 仅剩 node_modules 且无源码引用（旧前端已归档）
- [x] 4.2 删除 `frontend/` 目录（含 node_modules）
- [x] 4.3 删除工作区空日志文件：`.qwen-interpretation-304.log` 等 0 字节文件
- [x] 4.4 提交清理变更

## 5. 消除 utcnow 弃用告警

- [x] 5.1 定位全部 12 处 `datetime.utcnow()` 调用（`backend/app/`，含 `analysis_pipelines/checkpoints.py`、`analysis_pipelines/annotation_kinematics.py` 等）
- [x] 5.2 逐一替换为 `datetime.now(UTC)`（或 `datetime.now(timezone.utc)`），保持 UTC 语义不变
- [x] 5.3 运行全量测试确认无 DeprecationWarning、515 passed 保持
- [x] 5.4 提交 utcnow 修复

## 6. CI 卫生检查与最终验证

- [x] 6.1 在 `.github/workflows/ci.yml` 增加迁移文件完整性检查（head 迁移必须在 git 跟踪列表）
- [x] 6.2 在 CI 增加 `backend/uploads` 无跟踪产物检查（`git ls-files backend/uploads` 为空）
- [x] 6.3 运行全量后端测试 + 前端类型检查 + 前端 vitest 最终验证
- [x] 6.4 冒烟验证：本地 `alembic upgrade head` 幂等、后端应用可启动
- [x] 6.5 汇总提交 CI 变更并展示最终 `git status` / `git log` 结果
