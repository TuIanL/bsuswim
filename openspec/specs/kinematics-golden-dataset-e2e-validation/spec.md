# kinematics-golden-dataset-e2e-validation Specification

## Purpose
用版本化的真实衍生 fixture（`kinematics-golden.v1`：真实侧视视频 + 真实 CVAT 标注）验证二维运动学完整链路——上传、ingest、指标、资产、发现、五页报告、HTML 打印与 PDF——确保真实输入跨越所有系统边界后仍满足共同契约，而不是靠合成数据与 mock 通过。

## Requirements
### Requirement: The golden fixture is versioned and immutable

系统 SHALL 使用固定版本与 SHA-256 校验和的真实衍生 fixture（`kinematics-golden.v1`）验证二维运动学链路。

#### Scenario: Golden fixture is loaded

- **WHEN** golden validation suite 启动
- **THEN** 系统 SHALL 读取 `fixture_manifest.json`
- **AND** SHALL 校验视频与 CVAT XML 的 SHA-256
- **AND** checksum 不一致时 SHALL 立即失败
- **AND** MUST NOT 回退到 synthetic fixture
- **AND** manifest 声明路径 MUST NOT 逃逸 fixture 根目录

### Requirement: Real CVAT ingestion preserves the expected skeleton contract

系统 SHALL 使用真实 golden CVAT XML 验证骨架契约，且 ingestion 不得因未定义变量失败。

#### Scenario: Baseline XML is parsed

- **WHEN** 系统解析 golden `annotations.xml`
- **THEN** active annotated frame count SHALL 为 104
- **AND** active annotation frame range SHALL 为 0..104
- **AND** 每个 active frame SHALL 包含 17 个 COCO17 关节点
- **AND** baseline 中每个 active point visibility SHALL 非 `missing`
- **AND** all-outside track termination MUST NOT 形成重复 active frame
- **AND** `native_metadata.parsed_frame_count` SHALL 等于 active frame 数
- **AND** ingestion MUST NOT raise `NameError` from undefined warning variables

### Requirement: Golden frame mapping is explicit and verified

系统 SHALL 使用显式帧号表把 annotation frame 映射到 source video frame，不得以单一 affine stride 描述该序列。

#### Scenario: The golden annotation is normalized

- **WHEN** annotation frame mapping 被读取
- **THEN** `frame_mapping.mode` SHALL 为 `explicit`
- **AND** mapping SHALL 由 `source/frame_mapping.json` 逐条给出
- **AND** `source_original_offset` SHALL 为 270
- **AND** `annotation_fps_effective` SHALL 为 15
- **AND** `verified` SHALL 为 `true`
- **AND** `verification_reason` SHALL 为 `user_confirmed_source_frame_manifest`
- **AND** 序列中出现非等距间隔（490 → 498）时 MUST NOT 被单一 stride 规则覆盖

### Requirement: The pipeline produces the full canonical metric set

系统 SHALL 在 annotation_kinematics pipeline 完成时产出与 `side_2d_kinematics` 计算器 `CANONICAL_KEYS` 完全一致的指标集合；每个指标的 category 由该映射唯一确定。

#### Scenario: Golden annotation analysis completes

- **WHEN** annotation_kinematics pipeline 完成
- **THEN** AnnotationMetric schema SHALL 为 `swim-side-kinematics.v1`
- **AND** calculator SHALL 为 `side_2d_kinematics`
- **AND** summary 的 key 集合 SHALL 与 `CANONICAL_KEYS` 完全一致
- **AND** 禁止以单一数量断言（如 `==23`）作为唯一权威契约

### Requirement: Persisted metrics are numerically safe

系统 SHALL 保证持久化后的指标 payload 与报告 payload 不含 NaN / Infinity。

#### Scenario: Metrics and report are validated

- **WHEN** golden metrics 与报告被持久化
- **THEN** payload MUST NOT 包含 NaN
- **AND** MUST NOT 包含正负 Infinity

### Requirement: Five artifact classes are produced with verifiable files

系统 SHALL 生成五类视觉资产，且每个 ready 资产的文件与元数据可核验。

#### Scenario: Golden artifact generation completes

- **WHEN** artifact generation 完成
- **THEN** artifact plan SHALL 包含 `annotated_keyframe`、`time_series_chart`、`trajectory_chart`、`range_chart`、`radar_chart`
- **AND** 每个 ready artifact SHALL 存在实际文件
- **AND** `size_bytes` SHALL 等于实际文件大小
- **AND** `checksum_sha256` SHALL 等于实际文件校验和
- **AND** `mime_type` SHALL 非空
- **AND** 每个非 ready artifact SHALL 携带 `skip_reason`
- **AND** artifact URL SHALL 指向该 artifact 的 `/uploads/` 存储路径

### Requirement: Review findings are generated without unsupported conclusions

系统 SHALL 生成 review findings，且报告面不得出现无数据依据的确定性诊断。

#### Scenario: Golden review findings are generated

- **WHEN** `side_2d_kinematics_v1` 规则集运行完成
- **THEN** FindingSet status SHALL 为 `ready`
- **AND** 报告 claim-bearing 字段 MUST NOT 出现真实速度、划幅、SWOLF、推进力、阻力或功率

### Requirement: The structured report contains exactly five pages

系统 SHALL 装配严格包含 5 个 section 的 `side_2d_kinematics_5page_v1` 报告，页序与 profile 一致。

#### Scenario: Golden report is assembled

- **WHEN** five-page report assembly 完成
- **THEN** `schema_version` SHALL 为 `swim-report.v1`
- **AND** `report_profile` SHALL 为 `side_2d_kinematics_5page_v1`
- **AND** `sections` length SHALL 严格等于 5
- **AND** `page_number` SHALL 为 `[1,2,3,4,5]` 且唯一
- **AND** 页面顺序 SHALL 为：1 analysis_overview · 2 body_posture_control · 3 upper_limb_kinematics · 4 lower_limb_kinematics · 5 review_and_retest

### Requirement: All products trace to one annotation revision

系统 SHALL 保证指标、资产、发现与报告全部可追溯至同一 NormalizedAnnotation revision。

#### Scenario: Golden output provenance is checked

- **WHEN** pipeline 完成全部产物
- **THEN** `ArtifactSet.source_annotation_revision` SHALL 等于 `NormalizedAnnotation.revision`
- **AND** `FindingSet.source_annotation_revision` SHALL 等于同一 revision
- **AND** `report.source_trace.annotation_metric.source_revision` SHALL 等于同一 revision
- **AND** `report.source_trace.annotation_metric.revision_status` SHALL 为 `current`
- **AND** 报告 SHALL 携带 `generation_signature`
- **AND** 系统 MUST NOT 静默混用其他 revision

### Requirement: Missing keypoints degrade only affected outputs

系统 SHALL 在缺失关节点时仅降级受影响模块，整条任务不得失败。

#### Scenario: Right wrist is missing in all active frames

- **WHEN** right-wrist 在所有 active frame 中被标记为 missing
- **THEN** ingestion SHALL 成功
- **AND** annotation pipeline SHALL 完成
- **AND** `right_elbow_angle_deg` 时间序列 SHALL 无可用值
- **AND** `ArtifactSet.status` SHALL 为 `partial`
- **AND** SHALL 至少存在一个 `status=skipped` 且带 `skip_reason` 的 artifact
- **AND** `FindingSet.status` SHALL 保持 `ready`
- **AND** report `status` SHALL 为 `partial`
- **AND** report SHALL 仍包含五个 sections，其中 `upper_limb_kinematics` 页 status SHALL 为 `partial` 或 `unavailable`

### Requirement: HTML and PDF represent the same report

系统 SHALL 保证 HTML 报告、print-data 与导出的 PDF 使用相同的 generation signature 与页结构。

#### Scenario: Golden PDF is exported

- **WHEN** 系统从 golden ReportData 导出 PDF
- **THEN** report 与其 `source_trace` 的 `report_generation_signature` SHALL 一致
- **AND** 导出响应 `pdf_status` SHALL 为 `exported`
- **AND** 下载内容 SHALL 以 `%PDF` 开头
- **AND** PDF SHALL 严格包含 5 页

### Requirement: PDF page count is exactly five

系统 SHALL 保证 PDF 实际页数严格等于 5，布局溢出时阻止导出而非静默截断。

#### Scenario: Report data and rendered output respect the five-page contract

- **WHEN** golden report 被渲染和导出
- **THEN** HTML DOM 中 `.print-page` 数量 SHALL 为 5
- **AND** 每个 print page 不得出现布局溢出
- **AND** 生成的 PDF 实际页数 SHALL 严格等于 5
- **AND** 每页 SHALL 包含对应 page semantic marker（ASCII 格式 `P{n} | {page_type}`）
- **AND** 布局溢出 SHALL 设置 `__REPORT_PRINT_ERROR__ = { code: "PRINT_LAYOUT_OVERFLOW", pageNumber }` 并阻止导出

### Requirement: Unsupported conclusions are rejected

系统 SHALL 拒绝在 claim-bearing 字段中出现无数据依据的确定性结论。

#### Scenario: The report claim surface is validated

- **WHEN** golden ReportData 被验收
- **THEN** claim-bearing 字段 MUST NOT 包含真实速度、划幅、SWOLF、推进力、阻力或功率
- **AND** 这些术语 MAY 出现在 analysis boundaries、limitations 或 disclaimer，但 SHALL 明确表达当前系统不提供或无法计算

### Requirement: Golden baselines require explicit approval

系统 SHALL 要求 golden baseline 经显式脚本与批准原因更新，CI 不得自动接受新 baseline。

#### Scenario: A calculation change modifies expected results

- **WHEN** golden metric、finding、artifact plan 或 report contract 发生变化
- **THEN** contract 测试 SHALL 失败
- **AND** baseline MUST NOT 自动更新
- **AND** 更新 SHALL 通过 `scripts/build_kinematics_golden_fixture.py` 生成候选、`scripts/approve_kinematics_golden_baseline.py` 人工审批

### Requirement: Existing synthetic snapshot is demoted, not auto-overwritten

系统 SHALL 将旧 synthetic snapshot 降级为受控 structure contract，不与真实 golden fixture 共享 baseline。

#### Scenario: Legacy golden snapshot is migrated

- **THEN** 旧 `golden_five_page_report.json` SHALL 已重命名为 `synthetic_five_page_report_contract.json`
- **AND** 原测试 SHALL 降级为 synthetic structure contract
- **AND** 普通 pytest 运行 MUST NOT 自动写 baseline
- **AND** 真实 golden fixture SHALL 使用独立目录 `kinematics_golden_v1/expected/`

### Requirement: Video FPS and resolution provenance is correct in the kinematics report

系统 SHALL 在 `side_2d_kinematics_5page_v1` 报告中从 `SessionVideo` 读取权威 FPS 与 resolution，不读取未声明的 `VideoFile` 属性。

#### Scenario: Kinematics report reads authoritative video metadata

- **WHEN** `side_2d_kinematics_5page_v1` 报告构建 video context
- **THEN** FPS SHALL 取自 `SessionVideo.fps`
- **AND** resolution SHALL 取自 `SessionVideo.resolution`
- **AND** VideoFile 仅用于文件身份（id、filename）
- **AND** 无权威持久化时长时 `duration_sec` SHALL 为 `null`
- **AND** 报告构建器 MUST NOT 读取未声明的 `VideoFile.fps` / `VideoFile.width` / `VideoFile.height` / `VideoFile.duration_sec`

### Requirement: Artifact quality notes are scoped to their source module

系统 SHALL 让 artifact quality note 携带来源信息，并按来源模块过滤后再进入报告页面。

#### Scenario: A skipped or degraded artifact produces a note

- **WHEN** 一个 artifact 被 skipped 或降级
- **THEN** 该 note SHALL 携带 `module_key`、`artifact_key`、`metric_keys`
- **AND** 页面组装 SHALL 只接收与页面 source modules 匹配的 note
