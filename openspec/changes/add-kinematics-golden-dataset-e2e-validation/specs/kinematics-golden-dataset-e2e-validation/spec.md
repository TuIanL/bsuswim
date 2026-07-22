# Capability: kinematics-golden-dataset-e2e-validation

## ADDED Requirements

### Requirement: The golden fixture is versioned and immutable

系统 SHALL 使用具有固定版本和文件校验和的真实衍生 fixture 验证二维运动学链路。

#### Scenario: Golden fixture is loaded

- **WHEN** golden validation suite 启动
- **THEN** 系统 SHALL 读取 `kinematics-golden.v1` manifest
- **AND** SHALL 校验视频、XML 和辅助 manifest 的 SHA-256
- **AND** checksum 不一致时 SHALL 立即失败
- **AND** MUST NOT 回退到 synthetic fixture

### Requirement: Real CVAT ingestion preserves the expected skeleton contract

系统 SHALL 在使用真实 golden CVAT XML 经由 annotation ingest API 处理时，保持骨架契约且 ingestion 不得因未定义变量失败。
#### Scenario: Baseline XML is ingested

- **WHEN** 系统通过 annotation ingest API 处理 golden annotations.xml
- **THEN** CVAT sequence frame count SHALL 为 356
- **AND** active annotated frame count SHALL 为 56
- **AND** active annotation frame range SHALL 为 0..55
- **AND** 每个 active frame SHALL 包含 17 个 COCO17 关节点
- **AND** baseline 中每个 active point visibility SHALL 为 visible
- **AND** all-outside track termination MUST NOT 形成额外 active frame
- **AND** ingestion SHALL NOT raise NameError from undefined warning variables

### Requirement: Golden frame mapping is explicit and verified

系统 SHALL 使用显式、人工确认且 verified 的 affine mapping 将 annotation frame 映射到 source video frame。
#### Scenario: The golden annotation is normalized

- **WHEN** annotation frame mapping 使用经过确认的 affine mapping
- **THEN** source_frame_offset SHALL 为 32
- **AND** source_frame_stride SHALL 为 1
- **AND** mapping verified SHALL 为 true
- **AND** mapping verification_reason SHALL 为 user_confirmed
- **AND** annotation frame 0 SHALL 映射到 source video frame 32
- **AND** annotation frame 55 SHALL 映射到 source video frame 87

### Requirement: The pipeline produces all four metric categories

系统 SHALL 在 annotation_kinematics pipeline 完成时产出 body_posture、upper_limb、lower_limb、head_trunk 四类指标。
#### Scenario: Golden annotation analysis completes

- **WHEN** annotation_kinematics pipeline 完成
- **THEN** AnnotationMetric schema SHALL 为 swim-side-kinematics.v1
- **AND** calculator SHALL 为 side_2d_kinematics
- **AND** summary SHALL 包含全部 canonical metric keys
- **AND** metric categories SHALL 恰好包含 body_posture、upper_limb、lower_limb、head_trunk

### Requirement: Persisted metrics are numerically safe

系统 SHALL 保证持久化后的指标 payload 不含 NaN/Infinity，且角度与时间序列满足数值安全契约。
#### Scenario: Metrics are validated

- **WHEN** golden metrics 被持久化
- **THEN** payload MUST NOT 包含 NaN
- **AND** MUST NOT 包含正负 Infinity
- **AND** 所有关节角度 SHALL 位于 0 至 180 度
- **AND** time series SHALL 按帧序单调排列
- **AND** 连续帧变化 SHALL 满足已批准的 metric continuity contract

### Requirement: Metric summary matches the calculator canonical key set

系统 SHALL 使 metric summary 的 key 集合与类别与 `side_2d_kinematics` 计算器的 CANONICAL_KEYS 完全一致，并以版本化 golden 契约锁定 key-set hash。
#### Scenario: Calculator canonical keys are authoritative

- **WHEN** golden AnnotationMetric summary 被构建
- **THEN** summary 的 key 集合 SHALL 与 `side_2d_kinematics` 计算器导出的 CANONICAL_KEYS 完全一致
- **AND** 每个 key 的 category SHALL 等于 CANONICAL_KEYS 中声明的 category
- **AND** 禁止以单一数量断言（如 ==23）作为唯一权威契约

#### Scenario: Golden baseline pins the key set hash

- **WHEN** golden metric contract 被批准
- **THEN** calculator_version SHALL 为 1.0.0
- **AND** 已批准 baseline SHALL 锁定有序 canonical-key 列表及其 key-set SHA-256
- **AND** key-set 变更但未提升 calculator version SHALL 使校验失败

### Requirement: Representative frames reference valid source data

系统 SHALL 保证每个 representative frame 引用的 annotation frame 与 source video frame 均位于有效范围且可解码。
#### Scenario: Representative frames are generated

- **WHEN** 一个 metric 具有 representative frame
- **THEN** annotation_frame SHALL 位于 0..55
- **AND** annotation frame SHALL 存在于 NormalizedAnnotation
- **AND** verified mapping 下 source_video_frame SHALL 等于 annotation_frame + 32
- **AND** extractable representative frame SHALL 能从 golden video 精确解码

### Requirement: Five artifact classes are produced and accessible

系统 SHALL 生成五类视觉资产，且每个 ready 资产文件真实存在、校验和一致、可通过 URL 访问。
#### Scenario: Golden artifact generation completes

- **WHEN** artifact generation 完成
- **THEN** artifact plan SHALL 包含 annotated_keyframe、time_series_chart、trajectory_chart、range_chart、radar_chart
- **AND** 每个 ready artifact SHALL 存在实际文件
- **AND** actual checksum SHALL 与 persisted checksum 一致
- **AND** public asset URL SHALL 返回 HTTP 200
- **AND** response MIME SHALL 与 artifact metadata 一致

### Requirement: Review findings use valid evidence

系统 SHALL 保证 review findings 的证据 metric 与 frame 均有效，且不输出无数据依据的确定性诊断。
#### Scenario: Golden review findings are generated

- **WHEN** side_2d_kinematics_v1 规则集运行完成
- **THEN** FindingSet SHALL 为 ready
- **AND** 每个 finding status SHALL 为 review_required
- **AND** 每个 evidence metric SHALL 指向已存在的 metric
- **AND** 每个 evidence frame SHALL 位于有效帧范围
- **AND** findings MUST NOT 输出无数据依据的确定性诊断

### Requirement: The structured report contains exactly five pages

系统 SHALL 装配严格包含 5 个 section 的 `side_2d_kinematics_5page_v1` 报告，页序与 profile 一致。
#### Scenario: Golden report is assembled

- **WHEN** five-page report assembly 完成
- **THEN** schema_version SHALL 为 swim-report.v1
- **AND** report_profile SHALL 为 side_2d_kinematics_5page_v1
- **AND** sections length SHALL 严格等于 5
- **AND** page_number SHALL 为 [1,2,3,4,5]
- **AND** 每个 page_number SHALL 唯一
- **AND** 页面顺序 SHALL 与 report profile 一致：
  - page 1 = analysis_overview
  - page 2 = body_posture_control（合并 body_posture + head_trunk）
  - page 3 = upper_limb_kinematics
  - page 4 = lower_limb_kinematics
  - page 5 = review_and_retest

### Requirement: All products trace to one annotation revision

系统 SHALL 保证指标、资产、发现与报告全部可追溯至同一 NormalizedAnnotation revision。
#### Scenario: Golden output provenance is checked

- **WHEN** pipeline 完成全部产物
- **THEN** AnnotationMetric.source_revision SHALL 等于 NormalizedAnnotation.revision
- **AND** ArtifactSet.source_annotation_revision SHALL 等于该 revision
- **AND** FindingSet.source_annotation_revision SHALL 等于该 revision
- **AND** report source trace SHALL 引用相同 revision
- **AND** 各产物的动态数据库 ID SHALL 非空且相互引用一致（不锁定固定 ID 值）
- **AND** 系统 MUST NOT 静默混用其他 revision

### Requirement: Missing keypoints degrade only affected outputs

系统 SHALL 在缺失关节点时仅降级受影响模块，整条任务不得失败，且专项降级说明只落到对应页面。
#### Scenario: Right wrist is missing in all active frames

- **WHEN** right-wrist 在所有 active frame 中被标记为 missing
- **THEN** ingestion SHALL 成功
- **AND** annotation pipeline SHALL 完成
- **AND** right_elbow_angle_deg SHALL 为 unavailable
- **AND** left_elbow_angle_deg SHALL 保持可用或低置信度
- **AND** body posture、lower limb 和 head trunk MUST NOT 因此被整体阻塞
- **AND** 右肘关键帧资产 MAY 被 skipped
- **AND** report SHALL 仍然包含五个 sections
- **AND** report page 3 upper_limb_kinematics SHALL 包含右腕缺失导致的上肢指标或资产降级说明
- **AND** report page 2 body_posture_control 与 page 4 lower_limb_kinematics MUST NOT 包含该 upper-limb 专项降级说明

### Requirement: HTML and PDF represent the same report

系统 SHALL 保证 HTML 报告、print-data 与导出的 PDF 使用相同的 generation signature 与页结构。
#### Scenario: Golden PDF is exported

- **WHEN** 系统从 golden ReportMetadata 导出 PDF
- **THEN** HTML 和 print-data SHALL 使用相同 generation signature
- **AND** HTML SHALL 渲染 5 个 report sections
- **AND** PDF SHALL 严格包含 5 页
- **AND** PDF 每页 SHALL 包含对应 page semantic marker
- **AND** PDF 页序和标题 SHALL 与 ReportData sections 一致

### Requirement: PDF page count is exactly five

系统 SHALL 保证 PDF 实际页数严格等于 5，布局溢出时阻止导出而非静默截断。
#### Scenario: Report data and rendered output respect the five-page contract

- **WHEN** golden report 被渲染和导出
- **THEN** ReportData.sections.length SHALL 为 5
- **AND** HTML DOM 中 `.print-page` 数量 SHALL 为 5
- **AND** 每个 print page 不得出现布局溢出
- **AND** 生成的 PDF 实际页数 SHALL 严格等于 5
- **AND** 布局溢出 SHALL 设置 `__REPORT_PRINT_ERROR__` 且阻止导出，而非静默截断

### Requirement: Unsupported conclusions are rejected

系统 SHALL 拒绝在 claim-bearing 字段中出现无数据依据的确定性结论（速度、划幅、SWOLF、推进力等）。
#### Scenario: The report claim surface is validated

- **WHEN** golden ReportData 被验收
- **THEN** claim-bearing fields MUST NOT 包含真实速度、划幅、SWOLF、推进力、阻力或功率等无数据支持的指标或结论
- **AND** 这些术语 MAY 出现在 analysis boundaries、limitations 或 disclaimer
- **AND** 出现时 SHALL 明确表达当前系统不提供或无法计算

### Requirement: Golden baselines require explicit approval

系统 SHALL 要求 golden baseline 经显式脚本与批准原因更新，CI 不得自动接受新 baseline。
#### Scenario: A calculation change modifies expected results

- **WHEN** golden metric、finding、artifact plan 或 report contract 发生变化
- **THEN** CI SHALL 失败
- **AND** baseline MUST NOT 自动更新
- **AND** 开发者 SHALL 生成候选差异
- **AND** 变更 SHALL 关联明确的 OpenSpec change 和批准原因

### Requirement: Existing synthetic snapshot is demoted, not auto-overwritten

系统 SHALL 将现有自动覆盖的 synthetic snapshot 降级为受控 structure contract，不与真实 golden fixture 共享 baseline。
#### Scenario: Legacy golden snapshot is migrated

- **WHEN** Change 9 落地
- **THEN** `golden_five_page_report.json` SHALL 重命名为 `synthetic_five_page_report_contract.json`
- **AND** 原测试 SHALL 降级为 synthetic structure contract
- **AND** 普通 pytest 运行 MUST NOT 自动写 baseline
- **AND** synthetic contract 仅断言 schema_version、report_profile、sections 数量、page_number、page_type
- **AND** 真实 golden fixture SHALL 使用独立目录 `kinematics_golden_v1/expected/`

### Requirement: Video FPS and resolution provenance is correct in kinematics report

系统 SHALL 在 `side_2d_kinematics_5page_v1` 报告中从 `SessionVideo` 读取权威 FPS 与 resolution，不读取未声明的 VideoFile 属性。
#### Scenario: Kinematics report reads authoritative video metadata

- **WHEN** `side_2d_kinematics_5page_v1` 报告构建 video context
- **THEN** FPS SHALL 取自 `SessionVideo.fps`
- **AND** resolution SHALL 取自 `SessionVideo.resolution`
- **AND** VideoFile 仅用于文件身份（id、filename、checksum）
- **AND** 无权威持久化时长时 duration_sec SHALL 为 null
- **AND** 报告构建器 MUST NOT 读取未声明的 `VideoFile.fps`、`VideoFile.width`、`VideoFile.height`、`VideoFile.duration_sec`
- **AND** report.context.video.fps SHALL 等于绑定 SessionVideo 的 FPS
- **AND** report.context.video.resolution SHALL 等于 SessionVideo.resolution
- **AND** 其他 report profile 不在本 Change 范围

### Requirement: Artifact quality notes are scoped to their source module page

系统 SHALL 将 artifact quality notes 按来源模块作用域到对应页面，避免跨页泄漏。
#### Scenario: Upper-limb degradation note placement

- **WHEN** 一个 upper-limb artifact 被 skipped 或降级
- **THEN** 对应 quality note SHALL 只出现在 page 3 upper_limb_kinematics
- **AND** MUST NOT 出现在 page 2 body_posture_control 或 page 4 lower_limb_kinematics
- **AND** page 5 review_and_retest MAY 汇总该降级情况
