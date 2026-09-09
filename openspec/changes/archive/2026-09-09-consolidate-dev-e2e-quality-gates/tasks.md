## 1. 范围和 fixture 决策

- [x] 1.1 复核现有 `add-kinematics-golden-dataset-e2e-validation`，列出本 Change 接管的最小任务范围，并避免重复实现已完成内容
- [x] 1.2 根据 XML 和视频实际帧序列确定 `kinematics_golden_v1` 的 mapping 表示方式；非等距数据不得继续使用不成立的单一 affine 假设
- [x] 1.3 决定 golden MP4 使用 Git LFS、受控 artifact 或缩小后本地 fixture，并把选择写入 fixture README 和 CI 文档
- [x] 1.4 建立 `kinematics_golden_v1` 的目录、manifest、expected 和 mutations 目录结构
- [x] 1.5 补齐 manifest 中引用的 source、expected 和 mutation 文件，并写入真实 SHA-256

## 2. Fixture 和 baseline 基础能力

- [x] 2.1 实现 fixture loader：校验 manifest、路径、文件 hash、mapping 和版本字段
- [x] 2.2 为缺失文件、hash 不匹配和 mapping 不一致增加明确失败信息，并禁止 synthetic fallback
- [x] 2.3 实现 declarative mutation recipe 读取器，生成缺失右腕等测试变体
- [x] 2.4 增加 fixture contract tests，覆盖完整 fixture、缺文件、hash 错误和非等距映射
- [x] 2.5 将自动覆盖的 `golden_five_page_report.json` 迁移为只读 synthetic baseline
- [x] 2.6 增加 candidate baseline 生成和显式批准命令，输出结构、指标、发现、资产和页面差异

## 3. 后端测试可重复性和真实 contract

- [x] 3.1 增加后端 pytest 项目配置，声明 `pythonpath`、测试目录和 `golden_contract`/`golden_e2e` markers
- [x] 3.2 验证后端测试从仓库根目录和 `backend/` 目录运行时具有一致的导入和发现行为
- [x] 3.3 编写 golden contract 测试：真实 annotation/video 输入经过 ingestion、标准化和分析 pipeline
- [x] 3.4 验证指标 payload 不含 NaN/Infinity，时间序列单调，代表帧均落在已验证 mapping 内
- [x] 3.5 验证 metric、artifact、finding、report 的 source annotation revision 全链路一致
- [x] 3.6 验证五类 artifact 的状态、文件、checksum、MIME、尺寸和可访问性契约
- [x] 3.7 验证报告包含五个有序 section，并拒绝无数据依据的确定性指标/结论

## 4. 缺失关键点和报告打印链路

- [x] 4.1 使用 mutation recipe 生成缺失右腕变体，并验证受影响指标/资产降级而非整条任务失败
- [x] 4.2 修复 normalized annotation 创建流程中 SessionVideo 上下文查询使用错误 ORM 类型的问题
- [x] 4.3 修正 PrintReportView 的页面结构，确保不额外生成封面页且最终只有五个打印页
- [x] 4.4 修正 PrintReportView 的 ready/error 状态：图片或字体失败必须进入错误状态，不得在 `finally` 中无条件 ready
- [x] 4.5 增加打印页面语义标记、generation signature 和布局溢出预检
- [x] 4.6 编写 Playwright full-stack E2E：真实 HTTP、前端 print route 和 PDF renderer 均不 mock
- [x] 4.7 验证 HTML/PDF 的 generation signature、页面顺序、页面标记和 PDF 页数一致

## 5. 开发环境上传限制

- [x] 5.1 在配置中增加独立的视频和标注上传大小上限，并支持环境变量覆盖
- [x] 5.2 在流式保存过程中执行视频大小限制，超限时停止写入并清理 partial file
- [x] 5.3 在 annotation upload 路径执行大小限制，确保超限文件不会进入 parser 或创建持久记录
- [x] 5.4 统一 HTTP 413 和 `UPLOAD_TOO_LARGE` 错误响应，返回可供前端展示的限制信息
- [x] 5.5 增加视频和标注的低于上限、等于上限、超过上限和 partial cleanup 测试
- [x] 5.6 修复前端视频替换流程，使“替换侧面视频”真正打开选择器并更新绑定状态

## 6. CI 质量门禁

- [x] 6.1 在 CI backend job 中运行固定工作目录下的 pytest 和 fixture contract tests
- [x] 6.2 在 CI frontend job 中增加 Vitest，并保留 `vue-tsc --noEmit` 与 production build
- [x] 6.3 增加 OpenSpec strict validation job，并让校验失败返回非零状态
- [x] 6.4 增加 Chromium/Playwright/FFmpeg 的 golden E2E job，明确 fixture 获取和 PostgreSQL 服务依赖
- [x] 6.5 区分 product assertion failure 与 fixture/browser/database/service setup failure，并在日志中输出稳定错误标识
- [x] 6.6 确认普通 PR 不会泄露私有 fixture 凭证，缺少 fixture 时不会静默标记 golden E2E 为通过
- [x] 6.7 为 fast checks 和 full golden checks 编写本地运行命令及所需环境说明

## 7. 验收和收尾

- [x] 7.1 从仓库根目录执行后端测试、前端测试、前端构建和 OpenSpec strict validation
- [x] 7.2 在具备 fixture 和浏览器依赖的环境执行完整 golden contract 与 golden E2E
- [x] 7.3 检查 synthetic baseline、fixture manifest 和 expected 文件没有被普通测试自动改写
- [x] 7.4 更新开发文档，明确本 Change 已覆盖的能力和暂不覆盖的生产安全事项
- [x] 7.5 运行 `openspec validate consolidate-dev-e2e-quality-gates` 并确认 change artifacts 全部有效
