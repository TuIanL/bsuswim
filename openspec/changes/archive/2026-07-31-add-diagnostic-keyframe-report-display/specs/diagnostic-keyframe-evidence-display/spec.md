# diagnostic-keyframe-evidence-display Specification

## Purpose

定义自动诊断关键帧在游泳技术分析报告中的语义、分组、降级和跨 Web/PDF 展示契约。

## ADDED Requirements

### Requirement: Report exposes semantic diagnostic keyframe metadata

报告中的每个 ready 自动诊断关键帧 SHALL 保留原始 artifact identity，并提供面向教练阅读的展示语义，包括标题或标签、关联指标、数值和单位（可用时）、annotation frame、source video frame（可用时）和 source annotation revision。

#### Scenario: A ready keyframe is projected into a report section

- **WHEN** 当前 artifact set 包含 ready 的 `annotated_keyframe`
- **THEN** report asset SHALL 包含原始 `artifact_key` 和 `module_key`
- **AND** SHALL 包含展示标题、关联 metric key、指标展示值或明确的 unavailable 状态
- **AND** SHALL 保留 annotation frame、source video frame 和 source annotation revision

#### Scenario: Keyframe has no display value

- **WHEN** 关键帧资产没有可用的指标值
- **THEN** report asset SHALL 显示 `N/A` 或结构化 unavailable 状态
- **AND** SHALL NOT 填充估算值、0 或其他伪造数值

### Requirement: Keyframes are grouped with their diagnostic module

报告 SHALL 将关键帧放置在其原始 artifact module 对应的报告页面中，并使用稳定顺序展示。身体姿态和头躯干关键帧 SHALL 进入页面 2，上肢关键帧 SHALL 进入页面 3，下肢关键帧 SHALL 进入页面 4。

#### Scenario: Module keyframe assets are available

- **WHEN** 页面 2、3 或 4 组装当前资产
- **THEN** 页面 SHALL 只包含其 `source_module_keys` 范围内的关键帧
- **AND** 关键帧 SHALL 位于该页面图表资产之前或代表性证据区域内
- **AND** 页面 SHALL 保留原始 artifact module key

#### Scenario: A keyframe belongs to an unrelated module

- **WHEN** 关键帧的 module key 不属于目标页面 source module keys
- **THEN** 该关键帧 SHALL NOT 出现在目标页面
- **AND** SHALL NOT 被复制到其他模块页面

### Requirement: Keyframe evidence remains factual

关键帧展示 SHALL 只陈述现有运动学指标、骨架几何和帧定位事实，SHALL NOT 将指标极值自动解释为入水、抱水、推水、出水、移臂等动作阶段或确定性训练原因。

#### Scenario: A keyframe is selected by an angle extremum

- **WHEN** 关键帧由某个角度的最小值或最大值选择
- **THEN** 展示 SHALL 说明对应指标和选择含义
- **AND** SHALL NOT 把该图片标记为未经识别的动作阶段

### Requirement: Keyframe failures degrade without blocking the report

关键帧缺失、跳过或生成失败 SHALL 保留模块级质量说明，并且 SHALL NOT 阻塞五页报告或其他 ready 资产的展示。

#### Scenario: One keyframe is skipped

- **WHEN** 某个关键帧因 frame mapping、metric unavailable 或视频解码问题被 skipped/failed
- **THEN** 该资产 SHALL 不作为 ready 图片展示
- **AND** 所属页面 SHALL 保留可读的质量说明
- **AND** 同一模块的其他 ready 资产 SHALL 继续展示

### Requirement: Web and PDF use the same keyframe evidence

报告 Web 页面和打印 PDF SHALL 使用同一份 ReportData 中的关键帧集合、顺序、标题、指标值和帧定位信息。

#### Scenario: A report is rendered to HTML and PDF

- **WHEN** 当前报告同时打开 Web view 和 print route
- **THEN** 两者 SHALL 包含相同的关键帧 artifact keys
- **AND** SHALL 使用相同的 source annotation revision
- **AND** PDF SHALL 保留关键帧标题和指标说明
