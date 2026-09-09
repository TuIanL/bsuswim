## Context

当前项目由 FastAPI 后端、Vue/Vite 前端、模型服务和 PostgreSQL/Alembic 组成。后端测试和前端构建已经可以稳定通过，但测试底座仍存在几个开发阶段的结构性问题：真实 golden fixture 的帧映射和文件引用不一致，缺少完整的 API 到 PDF 的真实 E2E，CI 不运行前端测试，pytest 的导入行为依赖当前工作目录，synthetic baseline 可能在测试期间被覆盖。

现有 `add-kinematics-golden-dataset-e2e-validation` 已扩展到 167 项任务并处于进行中状态。本 Change 不继续向该 change 追加任务，而是定义一套可独立落地的开发质量闭环，并在实现时只接管能够明确验收的最小范围。真实业务指标、生产级鉴权、私有对象存储和分布式任务队列不属于本 Change。

## Goals / Non-Goals

**Goals:**

- 建立可校验、可复现、缺失即失败的 `kinematics_golden_v1` fixture 约定。
- 以真实输入验证上传/导入、标准化标注、指标、报告、浏览器打印和 PDF 的最小端到端链路。
- 将后端测试、前端测试、前端构建和 OpenSpec strict 校验纳入稳定的开发/CI 命令。
- 让浏览器 E2E 的产品失败和基础设施失败可区分，避免测试静默跳过或错误归因。
- 给视频和标注上传增加有限、可配置、适合本地开发的资源上限。
- 保证 baseline 只能通过显式命令更新，并修复真实链路暴露的最小开发阻塞问题。

**Non-Goals:**

- 不实现完整的生产级资源鉴权、私有文件存储、登录限流或 token 轮换。
- 不引入 Celery/Dramatiq 等分布式任务队列。
- 不增加新的运动学指标、诊断规则或姿态模型。
- 不进行 PDF 像素级快照比较，也不要求不同操作系统生成相同的 PDF 二进制。
- 不在本 Change 中自动归档或重写现有巨型 golden dataset change。

## Decisions

### 1. 将 fixture、contract 和 full-stack E2E 分层

新增三个可独立运行的测试层：

- `fixture_contract`：校验 manifest、文件 hash、帧映射、expected 和 mutation 引用。
- `golden_contract`：从真实 XML/视频进入后端分析和报告组装，验证结构、数值范围和 revision trace。
- `golden_e2e`：通过真实 HTTP、前端 print route 和 Playwright 导出 PDF，验证最终页面和 PDF。

这样可以让普通开发快速运行前两层，同时让浏览器和大视频依赖集中在独立 job 中。

### 2. 帧映射以实际证据为准

不预先固化旧 change 中存在冲突的 `offset=32/stride=1` 或 `stride=4` 假设。fixture manifest 必须声明一种可完整表达真实数据的 mapping：恒定 affine 时声明 offset/stride，存在缺帧或非等距时使用 explicit entries 或分段 mapping。loader 和 contract test 必须逐条验证 XML annotation frame、source video frame 和缺失帧关系。

### 3. Fixture 缺失时失败，不回退 synthetic

fixture loader 只接受完整且 hash 匹配的 fixture。若视频或 expected 文件缺失，测试失败并给出准备指引；不得自动切换到 synthetic 数据。CI 可以把需要私有视频的 `golden_e2e` 放到 nightly/manual job，但 job 必须显式报告 `E2E_INFRA_ERROR`，不能伪装成通过或静默跳过。

### 4. 采用双层 CI 门禁

Pull Request 的快速 job 运行后端 pytest、前端 Vitest、前端 build、fixture contract 和 OpenSpec strict validation。依赖大视频、Chromium 和完整前端服务的 `golden_e2e` 先作为 nightly/manual job，并保留清晰的失败状态；当环境稳定后再升级为 required check。此方案兼顾开发反馈速度和真实链路覆盖。

### 5. 通过项目配置消除 CWD 依赖

后端在 `backend/pytest.ini` 或等价的项目配置中声明 `pythonpath = .`、测试目录和 markers。所有文档和 CI 从仓库根目录使用固定命令，测试本身不依赖调用者先 `cd backend`。

### 6. 上传上限只做资源保护，不扩展生产安全模型

新增视频和标注的独立配置项，在流式写入时累计字节数，超过上限立即停止并删除部分文件，返回稳定的 HTTP 413 错误。默认值适合本地开发，环境变量可覆盖；本 Change 不要求视频接口完整接入用户授权。

### 7. Baseline 采用显式更新流程

普通测试只读 baseline。新增 candidate 生成命令和人工批准命令；批准时输出 schema、指标、发现、资产和报告页的差异，并要求提供 change 标识或原因。这样可以避免测试运行后悄悄改变仓库文件。

### 8. 只修复会阻塞开发闭环的最小问题

实现期允许修复 normalized annotation 创建时错误的 ORM 查询、视频替换流程未真正选择文件、PrintReportView 将图片解码失败视为成功等问题。若修复会改变正式业务语义或扩大到生产安全，则另开 change。

## Risks / Trade-offs

- **真实视频不可公开提交** → 支持本地 fixture 或受控 artifact 下载，并用 SHA-256 校验；普通 PR 不泄露下载凭证。
- **Chromium/FFmpeg 环境差异** → 锁定安装步骤并区分 product assertion 与 infrastructure setup failure；PDF 只比较页数和语义标记。
- **测试耗时增加** → 默认快速 job 不运行 full-stack PDF E2E，开发者可按 marker 单独运行完整链路。
- **帧映射决策延迟** → contract test 先要求 manifest 明确表达实际数据，不允许用错误的单一 affine 规则掩盖缺帧。
- **上传大小默认值影响既有本地素材** → 通过环境变量覆盖，并在错误响应中返回实际限制值。

## Migration Plan

1. 新增 fixture contract、配置化测试命令和四个能力规格对应的测试骨架。
2. 确认 golden fixture 的实际帧映射和分发方式，补齐 expected/mutation 文件。
3. 接入后端 golden contract 和最小 full-stack E2E。
4. 在 CI 中先启用快速 job，再启用 nightly/manual Chromium job。
5. 删除 synthetic baseline 的自动覆盖路径，确认现有单元测试仍通过。
6. 若浏览器 E2E 暂不稳定，可暂时停用其 job；不会影响应用运行和快速测试门禁。

## Open Questions

- 102MB golden MP4 最终使用 Git LFS、受控 artifact，还是缩小后的可提交 fixture？
- 实际数据中的非等距帧映射是使用 explicit mapping 还是分段 affine mapping？
- full-stack golden E2E 经过多少次稳定运行后升级为每个 PR 的 required check？
- 视频和标注的本地开发默认大小上限分别采用多少？
