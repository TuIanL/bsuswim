## Why

系统已经具备 CVAT XML ingestion、标准化标注、四类二维运动学指标、五类视觉资产、待复核发现、五页结构化报告、Web 报告渲染和 PDF 导出能力。但是，当前测试主要依赖合成骨架数据、服务级调用和被 mock 的 PDF renderer。现有测试尚不能证明一份真实的 CVAT Skeleton XML 与真实视频经过 Web/API 入口后，可以稳定完成以下完整链路：

视频上传 → 视频绑定 → CVAT XML ingestion → NormalizedAnnotation → 四类二维运动学指标 → 五类视觉资产 → 待复核发现 → 五页 swim-report.v1 → HTML 打印页面 → 五页 PDF

缺少这一验证意味着 parser、frame mapping、真实视频解码、文件存储、资产 URL、ReportData 投影、前端打印布局和 Playwright 导出之间仍可能存在只有在真实数据下才会暴露的契约漂移。本 Change 将现有真实游泳视频和 annotations.xml 制作为第一套版本化 golden fixture，并将其用于可复现的端到端验收。

## What Changes

- 新增 `kinematics-golden.v1` 真实衍生 fixture 包：经授权和脱敏处理的侧面视频片段、真实 CVAT Skeleton XML、可选的 CVAT image manifest、fixture manifest、文件校验和与预期契约。
- 明确 golden fixture 的固定 FPS、有效标注帧范围、17 点 schema 和 annotation-to-video frame mapping（affine，offset=32，stride=1，verified=user_confirmed）。
- 新增真实上传、绑定、ingest、分析、报告和 PDF 导出的端到端测试。
- 为指标输出增加有限值、合理范围和逐帧连续性断言。
- 验证 representative frame 只引用有效标注帧和有效视频帧。
- 验证五类视觉资产均能生成或按契约降级，ready 资产可以通过 URL 访问。
- 验证所有指标、资产、发现和报告均可追溯至同一 annotation revision。
- 新增缺失关节点变体，验证单个模块降级而不是整条任务失败。
- 验证结构化报告严格包含 5 个 section，打印 PDF 严格为 5 页。
- 验证 HTML、print-data 和 PDF 使用同一 report generation signature。
- 新增无数据依据结论保护，禁止报告输出真实速度、划幅、SWOLF、推进力、阻力和功率等当前数据无法支持的结论。
- 修复由真实 E2E 测试暴露的最小生产链路问题（CVAT ingestion warnings 变量覆盖、PrintReportView 额外封面页与无条件 ready、视频元数据投影读未声明字段、artifact quality note 跨页泄漏），但不扩展新的分析能力。
- 将现有自动覆盖的 `golden_five_page_report.json` 降为 synthetic structure contract，禁止普通测试自动改写 baseline。

## Capabilities

### New Capabilities

- `kinematics-golden-dataset-e2e-validation`: 系统 SHALL 使用版本化真实衍生 fixture 验证完整二维运动学报告链路；golden fixture SHALL 具有不可变输入校验和和人工批准的预期契约；完整 E2E SHALL 覆盖 HTML 和实际 Playwright PDF，而不是 mock renderer。

### Modified Capabilities

以下能力在本 Change 中发生需求级变更，均提供 delta spec（`specs/<capability>/spec.md`）：

- `cvat-xml-parse`: 真实 golden XML 暴露的 ingestion 最小修复（warnings 变量覆盖）与骨架契约断言。
- `automatic-annotation-ingestion-workflow`: 上传到 normalized annotation 的真实 API 链路断言。
- `side-2d-kinematics-metrics`: 四类指标安全性与连续性断言。
- `kinematics-visual-artifact-generation`: 五类资产文件/校验和/URL 断言与模块级 quality note 作用域。
- `2d-kinematics-review-findings`: finding 证据有效性断言。
- `five-page-kinematics-report`: 严格 5 页、模块级 quality note 作用域、视频元数据投影来源（SessionVideo.fps/resolution 而非 VideoFile 未声明属性）。
- `annotation-driven-analysis-pipeline`: pipeline 完成态与 source revision 贯穿断言。
- `swim-interactive-performance-report`: HTML/PDF 一致性语义比较。
- `pdf-export-service`: PDF 页数严格等于 5、布局溢出即失败、print-ready 不得无条件设置。

## Impact

### Test fixtures

- `backend/tests/fixtures/kinematics_golden_v1/`
- `backend/tests/golden/`
- `backend/tests/e2e/`
- `backend/tests/fixtures/golden_five_page_report.json` → 重命名为 `synthetic_five_page_report_contract.json` 并降级

### Backend

- CVAT ingestion 中被真实 fixture 暴露的最小修复（`normalized_annotation_service.py` warnings 变量覆盖）
- golden contract assertion helpers
- HTML/PDF semantic markers
- PDF 页数与内容验证工具
- `_build_video_context`（`reporting/kinematics_report/page_builders.py`）改读 `SessionVideo.fps` 与 `SessionVideo.resolution`
- artifact quality note 模块级过滤

### Frontend

- 修正 PrintReportView，使结构化五页报告只输出五个打印页
- print ready 仅在数据、字体和图片完成后设置
- 增加稳定的 report signature 和 page semantic attributes
- 增加布局溢出预检，溢出时设置 `__REPORT_PRINT_ERROR__`

### CI

- 新增 golden contract job（每个 PR 硬门禁）
- 新增 full-stack golden E2E job（发布级硬门禁，稳定后升级为每 PR required）
- 安装 PostgreSQL、Chromium 和必要的视频解码依赖

## Non-goals

- 不增加新的运动学指标
- 不修改诊断阈值
- 不训练或接入新的姿态识别模型
- 不增加正面、俯视、水下机位
- 不把 golden 数据变成公开训练数据集
- 不做像素级截图快照比较
- 不要求不同操作系统生成字节完全一致的 PDF
- 不对其他 report profile 做推测性视频元数据修复
