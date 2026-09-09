## Why

当前项目的单元测试和前端构建已经基本稳定，但开发环境仍缺少一条可重复验证的完整链路：真实标注数据、视频帧映射、分析任务、报告生成、浏览器打印和 PDF 导出之间没有共同的受控基线。与此同时，现有 golden dataset change 已扩大到 167 项任务，受到帧映射冲突、视频分发方式和缺失 expected 文件的阻塞，继续追加任务会进一步降低可维护性。

本 Change 将开发阶段最需要的验证能力收敛为一套较小的质量门禁：fixture 可复现、真实 E2E 可执行、CI 能运行关键测试、pytest/OpenSpec 行为稳定，并为本地视频上传增加不会明显影响开发便利性的资源上限。生产级鉴权、私有对象存储和分布式任务队列不在本 Change 内。

## What Changes

- 新增一个版本化、可复现的 `kinematics_golden_v1` fixture 约定，明确帧映射、缺帧处理、expected contract、mutation recipe 和 fixture 校验方式。
- 将现有黄金数据验证拆为可独立运行的 contract test 和 full-stack browser/PDF E2E，不允许缺 fixture 时静默回退到 synthetic 数据。
- 增加真实分析链路的最小 E2E：上传、标注导入、标准化、指标生成、报告生成、HTML 打印和 PDF 导出。
- 将前端 Vitest、后端 pytest 配置检查、fixture contract 和 OpenSpec strict 校验纳入 CI 质量门禁；Chromium E2E 单独提供可见的环境失败状态。
- 固化测试运行目录和依赖路径，避免测试结果依赖当前 shell 的 CWD。
- 为视频和标注上传增加开发环境可配置的文件大小上限，并明确超限错误契约；不在本 Change 内引入完整的生产级文件权限体系。
- 清理 synthetic report baseline 的自动覆盖行为，基线更新必须通过显式命令完成。
- 修复由真实链路暴露的最小开发阻塞问题，包括 normalized annotation 上下文查询、视频替换流程和 PDF 图片失败状态。

## Capabilities

### New Capabilities

- `development-golden-fixture`: 为开发和 CI 提供版本化、可校验、不会静默回退的真实衍生 fixture 及 expected contract。
- `development-e2e-validation`: 验证从视频/标注输入到 HTML/PDF 输出的最小真实端到端链路，并覆盖缺失关键点的降级行为。
- `development-quality-gates`: 统一 pytest、Vitest、OpenSpec strict 校验和浏览器 E2E 的本地/CI 执行契约。
- `development-upload-limits`: 为开发环境视频和标注上传提供可配置的大小上限、明确错误响应和测试覆盖。

### Modified Capabilities

暂不修改现有业务能力的正式需求。帧映射运行时语义、生产级资源鉴权和报告业务规则保持现状；本 Change 只新增开发验证与质量门禁能力，避免与现有 `add-kinematics-golden-dataset-e2e-validation` 重复修改相同业务规格。

## Impact

- 后端测试与 fixture：`backend/tests/fixtures/kinematics_golden_v1/`、`backend/tests/golden/`、`backend/tests/e2e/`、pytest 配置和测试辅助脚本。
- 后端运行时：视频/标注上传大小配置、normalized annotation 创建流程、分析链路 E2E 所需的最小修复。
- 前端：Vitest CI 执行、视频替换流程、PrintReportView 的失败状态处理。
- CI：`.github/workflows/ci.yml`，包括前端测试、OpenSpec strict 校验和 Chromium/Playwright E2E job。
- OpenSpec：新增四个开发阶段能力规格及对应 proposal/design/tasks artifacts。
- 依赖和开发环境：可能增加或明确 Playwright/Chromium、ffprobe、fixture 下载或本地 fixture 准备脚本，但不改变生产部署架构。
